"""
Verify that your queue-times.com cookies pass Cloudflare and that the
historical-data page actually renders.

Usage:
    .venv/bin/python scripts/verify_cookies.py
"""
import json
import sys
import re
from pathlib import Path

from curl_cffi import requests as cffi_requests


ROOT = Path(__file__).resolve().parent.parent
COOKIES_FILE = ROOT / "scripts" / "qt_cookies.json"
TEST_URL = "https://queue-times.com/en-US/parks/334/rides/14687?given_date=2025-10-16"

# Values to ignore when reading the cookies dict (people leave placeholders).
PLACEHOLDER_VALUES = {"PASTE_HERE", "N/A", "none", "null", "doesnt exist", ""}


def load_cookies() -> dict:
    if not COOKIES_FILE.exists():
        print(f"❌ {COOKIES_FILE} not found.")
        print("   Read scripts/COOKIE_SETUP.md for how to create it.")
        sys.exit(1)
    cfg = json.loads(COOKIES_FILE.read_text())
    if "user_agent" not in cfg or "cookies" not in cfg:
        print("❌ qt_cookies.json must have keys 'user_agent' and 'cookies'.")
        sys.exit(1)
    if "cf_clearance" not in cfg["cookies"] or not cfg["cookies"]["cf_clearance"].strip():
        print("❌ Missing cf_clearance cookie — that's the one that actually passes Cloudflare.")
        sys.exit(1)
    return cfg


def is_real(v: str) -> bool:
    if not v:
        return False
    lower = v.strip().lower()
    if lower in PLACEHOLDER_VALUES:
        return False
    if lower.startswith("paste"):
        return False
    return True


def main() -> int:
    cfg = load_cookies()
    ua = cfg["user_agent"]
    cookies = {k: v.strip() for k, v in cfg["cookies"].items() if is_real(v)}

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }

    print(f"Fetching {TEST_URL}")
    print(f"  cookies sent: {list(cookies.keys())}")
    print(f"  UA: {ua[:80]}…")
    print(f"  TLS impersonation: chrome (via curl_cffi)")

    # curl_cffi impersonates Chrome's TLS+JA3 fingerprint — this is what Cloudflare checks.
    r = cffi_requests.get(
        TEST_URL,
        headers=headers,
        cookies=cookies,
        impersonate="chrome",
        timeout=30,
    )

    print(f"\n  status: {r.status_code}  size: {len(r.text)} bytes")
    title = re.search(r"<title>([^<]*)</title>", r.text)
    print(f"  title: {title.group(1) if title else '<no title>'}")

    if r.status_code != 200:
        print(f"\n❌ Non-200 response. Cookies probably expired or User-Agent mismatch.")
        return 1

    if "Just a moment" in r.text or "challenge" in r.text.lower()[:5000]:
        print("\n❌ Still hitting the Cloudflare challenge page.")
        print("   Refresh queue-times.com in your browser and re-extract cf_clearance.")
        return 1

    # Look for telltale data markers
    found_markers = []
    for label, pat in [
        ("ride name H1/H2", r"Battle at the Ministry"),
        ("highcharts", r"[Hh]ighcharts|Chart\.js|chart\.min\.js"),
        ('script with "wait"', r"wait[_ ]?time|wait_minutes|temps_attente"),
        ("numeric series", r'series\s*:\s*\[|"data"\s*:\s*\[\d'),
        ("hh:mm timestamps", r'\[\s*"\d{1,2}:\d{2}"'),
        ("Time/Wait table", r"<th[^>]*>\s*(?:Time|Wait)"),
    ]:
        m = re.findall(pat, r.text)
        if m:
            found_markers.append(f"{label} ({len(m)} matches)")

    print(f"\n  markers found: {len(found_markers)}")
    for m in found_markers:
        print(f"    • {m}")

    out_html = Path("/tmp/qt_authed.html")
    out_html.write_text(r.text)
    print(f"\n  full HTML written to {out_html}  ({len(r.text)} bytes)")

    if not found_markers:
        print("\n⚠  Page came back but I don't see chart/data markers. Inspect /tmp/qt_authed.html.")
        return 2

    print("\n✓ cookies work — chart data should be extractable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
