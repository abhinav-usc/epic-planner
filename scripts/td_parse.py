"""
Parse a thrill-data per-attraction page and extract the embedded Plotly
heatmap as a list of (date, hour, wait_minutes) rows.

The data is embedded directly in a <script> tag as:
    Plotly.newPlot("<div-id>", [{...heatmap json...}], {...layout...}, ...)

We pick out the heatmap object whose `type == "heatmap"` and read its
`x` (hour labels), `y` (date labels), and `z` (matrix of wait strings).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Iterator, Optional


def find_heatmap_in_html(html: str) -> Optional[dict]:
    """Return the best Plotly heatmap trace dict from the page, or None.

    thrill-data embeds two heatmaps per page:
      - A 5-minute-bucket raw poll heatmap (x_len ≈ 170) sourced from
        queue-times.com — this one is capped at ~23 min for popular LL rides.
      - An hourly-aggregated summary heatmap (x_len ≤ 24) built from
        thrill-data's own aggregation — this is the one with real wait values.

    We prefer the hourly heatmap (x_len ≤ 24).  If multiple hourly heatmaps
    exist, take the one with the most data cells.  Fall back to the last
    heatmap found if none has an hourly x-axis.
    """
    candidates: list[dict] = []  # (x_len, cell_count, trace)

    for m in re.finditer(
        r'Plotly\.(?:newPlot|react)\s*\(\s*"[^"]+"\s*,\s*(\[)', html
    ):
        start = m.end() - 1
        depth = 0
        in_str = False
        esc = False
        end = -1
        for i in range(start, len(html)):
            ch = html[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            continue
        try:
            traces = json.loads(html[start:end])
        except json.JSONDecodeError:
            continue
        for trace in traces:
            if isinstance(trace, dict) and trace.get("type") == "heatmap":
                x = trace.get("x") or []
                z = trace.get("z") or []
                cell_count = sum(
                    1 for row in z for v in row
                    if v not in (None, "", "null")
                )
                candidates.append((len(x), cell_count, trace))

    if not candidates:
        return None

    # Prefer hourly (x_len ≤ 24); among those take the one with most cells.
    hourly = [(xl, cc, t) for xl, cc, t in candidates if xl <= 24]
    if hourly:
        return max(hourly, key=lambda item: item[1])[2]
    # Fallback: return the last heatmap found.
    return candidates[-1][2]


def hour_label_to_24(label: str) -> Optional[int]:
    """Convert '08:00 AM' / '01:00 PM' → 8 / 13. Returns None for 'Average' etc."""
    label = label.strip()
    try:
        return datetime.strptime(label, "%I:%M %p").hour
    except ValueError:
        return None


def date_label_to_iso(label: str) -> Optional[str]:
    """Convert '11/14/2025' → '2025-11-14'. Returns None for 'Average'."""
    label = label.strip()
    try:
        return datetime.strptime(label, "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def iter_heatmap_rows(html: str) -> Iterator[tuple[str, int, int]]:
    """
    Yield (date_iso, hour_24, wait_minutes) for every (date, hour) cell with
    a numeric value. Skips the "Average" row/column and empty cells.
    """
    trace = find_heatmap_in_html(html)
    if not trace:
        return
    x = trace.get("x") or []
    y = trace.get("y") or []
    z = trace.get("z") or []
    hour_map = {i: hour_label_to_24(lbl) for i, lbl in enumerate(x)}
    date_map = {i: date_label_to_iso(lbl) for i, lbl in enumerate(y)}
    for j, row in enumerate(z):
        date_iso = date_map.get(j)
        if not date_iso:
            continue
        for i, cell in enumerate(row):
            hour_24 = hour_map.get(i)
            if hour_24 is None:
                continue
            if cell in (None, "", "null"):
                continue
            try:
                wait = int(float(cell))
            except (TypeError, ValueError):
                continue
            yield date_iso, hour_24, wait


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/td_harrypotterandthebattleatthemi.html"
    html = open(path).read()
    rows = list(iter_heatmap_rows(html))
    print(f"Parsed {len(rows)} (date,hour,wait) cells")
    print("First 8:")
    for r in rows[:8]:
        print(f"  {r}")
    print("Last 4:")
    for r in rows[-4:]:
        print(f"  {r}")
    # Range of dates / hours
    dates = sorted(set(r[0] for r in rows))
    hours = sorted(set(r[1] for r in rows))
    print(f"\nDates covered: {len(dates)}  range={dates[0]} → {dates[-1]}")
    print(f"Hours covered: {hours}")
    waits = [r[2] for r in rows]
    if waits:
        print(f"Wait stats: min={min(waits)} max={max(waits)} mean={sum(waits)/len(waits):.1f}")
