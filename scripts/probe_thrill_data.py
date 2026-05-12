"""Probe thrill-data with camoufox to see if its Cloudflare is beatable."""
import re
import sys
from pathlib import Path
from camoufox.sync_api import Camoufox

URL = "https://www.thrill-data.com/waits/park/uor/epic-universe/"


def main():
    with Camoufox(headless=True, humanize=True, os="macos") as browser:
        page = browser.new_page()
        print(f"Loading {URL}")
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            print(f"goto error: {e}")
            return 1

        cleared = False
        for i in range(40):
            t = page.title()
            if t and "moment" not in t.lower() and "challenge" not in t.lower():
                cleared = True
                print(f"  cleared after {i}s, title={t!r}")
                break
            page.wait_for_timeout(1000)
        if not cleared:
            print(f"  STILL stuck after 40s, title={t!r}")
            return 1

        page.wait_for_timeout(4000)
        html = page.content()
        Path("/tmp/td_page.html").write_text(html)
        print(f"  HTML {len(html)} bytes → /tmp/td_page.html")

        # Look for anything useful
        for name, pat in [
            ("ride name list", r"Stardust Racers|Battle at the Ministry|Mario Kart"),
            ("Highcharts", r"[Hh]ighcharts"),
            ("chart.js", r"[Cc]hart\.?js"),
            ("Plotly", r"[Pp]lotly"),
            ("wait_time", r"wait[_ ]?time"),
            ("data series", r'series\s*:\s*\[|"data"\s*:\s*\['),
        ]:
            m = re.findall(pat, html)
            if m:
                print(f"  pattern {name!r}: {len(m)} hits")

        return 0


if __name__ == "__main__":
    sys.exit(main())
