"""
Try Camoufox (hardened Firefox) to bypass Cloudflare on queue-times.com.
"""
import re
import sys
from pathlib import Path
from camoufox.sync_api import Camoufox

URL = sys.argv[1] if len(sys.argv) > 1 else (
    "https://queue-times.com/en-US/parks/334/rides/14687?given_date=2025-10-16"
)


def main():
    with Camoufox(headless=True, humanize=True, os="macos") as browser:
        page = browser.new_page()
        print(f"Loading: {URL}")
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

        cleared = False
        for i in range(40):
            title = page.title()
            if title and "moment" not in title.lower() and "challenge" not in title.lower():
                print(f"  cleared after {i}s, title={title!r}")
                cleared = True
                break
            page.wait_for_timeout(1000)
        if not cleared:
            print(f"  STILL stuck, title={title!r}")
            return False

        page.wait_for_timeout(4000)
        html = page.content()
        Path("/tmp/qt_page.html").write_text(html)
        print(f"  HTML: {len(html)} bytes → /tmp/qt_page.html")

        # Pattern audit
        for name, pat in [
            ("series:[", r'series\s*:\s*\['),
            ("categories:[", r'categories\s*:\s*\['),
            ('["HH:MM", n]', r'\[\s*"\d{1,2}:\d{2}"\s*,\s*\d+\s*\]'),
            ("wait_time", r'wait[_ ]?time'),
            ("highcharts", r'[Hh]ighcharts'),
            ("data array", r'"data"\s*:\s*\[\s*\d+'),
            ("dataset", r'"datasets"\s*:'),
        ]:
            m = re.findall(pat, html)
            if m:
                print(f"  pattern {name!r}: {len(m)} hits  sample={m[0][:120]}")

        # If we found chart data, also print a longer snippet
        if "highcharts" in html.lower() or "chart" in html.lower():
            # Find the script tag containing the chart
            for match in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
                content = match.group(1)
                if "wait" in content.lower() or "series" in content.lower():
                    print(f"\n  ── candidate script chunk ({len(content)}B): ──")
                    print(content[:1500])
                    print("  ── /end ──")
                    break

        return cleared


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
