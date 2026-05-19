"""
Lightning Lane Multi Pass (LLMP) booking strategy.

Two functions:
  - predict_ll_earliest_return(): given a ride and a hypothetical booking time,
    estimate the earliest return-time slot you could grab. Heuristic, not learned.

  - optimize_ll_plan(): given a planned itinerary, return an ordered list of
    booking actions: which ride to book, when, expected return window, priority.

Approach (heuristic, no model dependency):
  - Tier × time-of-day × crowd is the main driver. Top-tier popular rides see
    their earliest return time push out fastest as the day progresses.
  - "Lock-in time" = the latest booking moment after which the predicted return
    time exceeds the planned ride time. Earlier lock-in → more urgent to book.
  - Optimizer sorts by lock-in (urgent first), then walks forward assigning
    booking slots respecting the "tap in to current LL before booking next" rule.

Why heuristic and not learned:
  - Public LL availability data isn't reliably scrapeable (no clean feed).
  - Tier + day-type + time-of-day captures the dominant pattern.
  - Constants are tunable as we learn from actual trip data.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Optional

from backend.data.attractions_db import Attraction


# Per-tier baselines: at park open (book_time = open), how many minutes from
# the booking moment until the earliest available LL return window opens.
# Calibrated against real-world community reports of DLR LLMP return windows.
TIER_BASE: dict[int, float] = {
    1: 10.0,
    2: 12.0,
    3: 18.0,
    4: 25.0,
    5: 60.0,
}

# Per-tier "ramp": minutes of return-time shift per minute of elapsed-since-open.
# A ramp of 0.5 means: 1 hour after open, the earliest-return-time offset has
# grown by 30 min beyond the base. Top-tier popular rides fill up fastest.
TIER_RAMP: dict[int, float] = {
    1: 0.05,
    2: 0.10,
    3: 0.15,
    4: 0.25,
    5: 0.50,
}

# LLMP queue time once you arrive at the ride during your return window.
LL_QUEUE_TIME = 10

# Day-crowd → ramp multiplier. Holidays push return windows out faster than
# normal days, but not 1:1 with crowd factor. Tuned so a 2.3× holiday crowd
# yields ~1.5× the pace of a normal day.
def _day_pace_multiplier(day_crowd: float) -> float:
    return 1.0 + 0.4 * max(0.0, day_crowd - 1.0)


def predict_ll_earliest_return(
    ride: Attraction,
    book_minute_from_open: float,
    day_crowd: float,
    park_open_minute: int = 0,
    park_close_minute: int = 13 * 60,
) -> int:
    """Estimate the earliest LL return window (minutes since park open) if you
    book `ride` at `book_minute_from_open`.

    Returns an integer minute-of-day (since park open). Always at least
    `book_minute_from_open + 15` (LL return windows can't be in the past).
    """
    tier_base = TIER_BASE.get(ride.tier, 30.0)
    tier_ramp = TIER_RAMP.get(ride.tier, 0.5)
    pace = _day_pace_multiplier(day_crowd)

    elapsed = max(0.0, book_minute_from_open - park_open_minute)
    base_offset = tier_base * pace
    ramp_offset = elapsed * tier_ramp * pace
    earliest_return = book_minute_from_open + base_offset + ramp_offset

    # Can't be in the past, and respect a minimum 15-min gap.
    earliest_return = max(book_minute_from_open + 15, earliest_return)
    return int(round(earliest_return))


@dataclass
class PlannedRide:
    attraction: Attraction
    planned_minute: int  # minutes since park open the user wants to ride
    must_do: bool = False


@dataclass
class LLBooking:
    attraction_id: str
    attraction_name: str
    book_at_minute: int            # when to book (minutes since park open; 0 = at open)
    predicted_return_minute: int   # earliest available return time after that booking
    savings_minutes: int           # standby - LL_QUEUE_TIME
    priority: str                  # "urgent" | "normal" | "skip"
    reason: str                    # one-line explanation

    def to_dict(self) -> dict:
        return asdict(self)


def _lock_in_minute(ride: Attraction, planned_minute: int, day_crowd: float, park_open_minute: int) -> float:
    """Latest book_time s.t. predict_ll_earliest_return(ride, book_time) + LL_QUEUE_TIME <= planned_minute.

    Lower values = "must book early." Negative = "must book before park open" (urgent).
    """
    tier_base = TIER_BASE.get(ride.tier, 30.0)
    tier_ramp = TIER_RAMP.get(ride.tier, 0.5)
    pace = _day_pace_multiplier(day_crowd)

    # earliest_return = book + base*pace + (book - open)*ramp*pace
    # want: earliest_return + LL_QUEUE_TIME <= planned_minute
    # i.e.: book * (1 + ramp*pace) <= planned_minute - LL_QUEUE_TIME - base*pace + open*ramp*pace
    rhs = planned_minute - LL_QUEUE_TIME - tier_base * pace + park_open_minute * tier_ramp * pace
    denom = 1.0 + tier_ramp * pace
    if denom <= 0:
        return float("inf")
    return rhs / denom


def optimize_ll_plan(
    planned_rides: list[PlannedRide],
    day_crowd: float,
    park_open_minute: int,
    park_close_minute: int,
    predict_standby: Optional[Callable[[Attraction, int], int]] = None,
    first_booking_minute: Optional[int] = None,
) -> list[LLBooking]:
    """Given a planned itinerary, return an ordered list of LL bookings.

    Strategy:
      1. Filter to LLMP-eligible rides (ll_type == "multi"). LLSP rides are handled
         separately (they're per-purchase, no return-time strategy).
      2. For each, compute lock-in minute (latest book time that still fits return
         before planned ride) and standby savings.
      3. Sort by lock-in ascending; ties broken by tier descending (top rides first)
         and must-do status.
      4. Walk forward: first booking at park open/arrival. Each subsequent booking
         follows the LLMP 2-hour rule: you may book again 2 hours after your last
         booking OR immediately after tapping in (scanning) — whichever is sooner.
      5. Flag rides where predicted return exceeds park close → skip.
      6. Since LLMP is a paid product, the skip threshold for savings is low (≥5 min);
         maximise use across the day for top-tier rides.
      7. Flag rides where predicted return > planned_minute + 60 → urgent.
    """
    llmp = [pr for pr in planned_rides if pr.attraction.ll_type == "multi"]
    if not llmp:
        return []

    # Compute lock-in + savings per ride
    scored: list[tuple[PlannedRide, float, int]] = []
    for pr in llmp:
        lock_in = _lock_in_minute(pr.attraction, pr.planned_minute, day_crowd, park_open_minute)
        if predict_standby is not None:
            standby = predict_standby(pr.attraction, pr.planned_minute)
        else:
            # Reasonable default based on tier + crowd
            tier_baseline = {1: 8, 2: 15, 3: 30, 4: 55, 5: 80}.get(pr.attraction.tier, 30)
            standby = int(tier_baseline * day_crowd)
        savings = max(0, standby - LL_QUEUE_TIME)
        scored.append((pr, lock_in, savings))

    # Sort by lock-in ascending; break ties by tier descending (top rides first),
    # then must-do, so high-value rides claim early slots when urgency is equal.
    scored.sort(key=lambda x: (x[1], -x[0].attraction.tier, not x[0].must_do))

    # Walk forward assigning booking slots.
    # LLMP 2-hour rule: you may book the next LL either:
    #   (a) 2 hours after your last booking, OR
    #   (b) immediately after you tap in (scan) at your return window
    # — whichever comes first. This lets you squeeze in extra bookings when
    # return windows are short, and also book after 2h even if not yet tapped in.
    bookings: list[LLBooking] = []
    next_book_at = float(
        first_booking_minute if first_booking_minute is not None else park_open_minute
    )
    last_book_at = next_book_at  # tracks the moment of the previous booking

    LL_REBOK_INTERVAL = 120  # LLMP 2-hour rebooking window

    for pr, lock_in, savings in scored:
        ride = pr.attraction
        return_min = predict_ll_earliest_return(
            ride, next_book_at, day_crowd, park_open_minute, park_close_minute
        )

        slip = return_min - pr.planned_minute
        if return_min >= park_close_minute:
            priority = "skip"
            reason = "Predicted LL return is past park close — won't fit."
        elif savings < 5:
            # Low threshold since LLMP is prepaid — only skip truly negligible saves
            priority = "skip"
            reason = f"LL saves ~{savings} min — barely worth the tap."
        elif slip > 60:
            priority = "urgent"
            reason = f"Earliest return is ~{slip} min past your planned visit — book first or expect to shift."
        elif slip > 30 and pr.must_do:
            priority = "urgent"
            reason = f"Must-do; earliest return slips ~{slip} min — book early."
        else:
            priority = "normal"
            reason = ""

        bookings.append(LLBooking(
            attraction_id=ride.id,
            attraction_name=ride.name,
            book_at_minute=int(next_book_at),
            predicted_return_minute=return_min,
            savings_minutes=savings,
            priority=priority,
            reason=reason,
        ))

        if priority == "skip":
            continue

        # 2-hour rule: next booking = min(2h after this booking, tap-in time)
        tap_in_time = return_min + LL_QUEUE_TIME
        last_book_at = next_book_at
        next_book_at = min(last_book_at + LL_REBOK_INTERVAL, tap_in_time)

    # Output in chronological booking order
    bookings.sort(key=lambda b: b.book_at_minute)
    return bookings
