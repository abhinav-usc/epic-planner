# Extracting queue-times.com cookies (one-time setup)

Cloudflare blocks any automated browser we throw at queue-times.com.
The workaround: you complete the Cloudflare challenge once in your real Chrome,
then we re-use your `cf_clearance` cookie + your User-Agent to scrape.

## Step 1 — Pass Cloudflare in your browser

1. Open Chrome.
2. Visit: <https://queue-times.com/en-US/parks/334/rides/14687?given_date=2025-10-16>
3. You'll see "Just a moment…" for a few seconds while Cloudflare verifies.
4. Wait until the **actual page loads** — you should see the ride name "Harry Potter and the Battle at the Ministry" and a wait-time chart.
   - If you stay stuck on "Just a moment…", refresh the page. Sometimes click the Cloudflare checkbox if it appears.

## Step 2 — Copy the cookies

1. With that page open, press **F12** (or Cmd+Opt+I on Mac) to open DevTools.
2. Click the **Application** tab (top bar of DevTools).
3. On the left sidebar, expand **Cookies** → click **https://queue-times.com**.
4. You'll see a table of cookies. **I need these specific rows** (case-sensitive names):
   - `cf_clearance` ← **most important**

   > dFOwgIa_4Si4S7UGoiQ34bLFzsBmdW1zGq2TgLYO3Ro-1778585875-1.2.1.1-qbfHot6PwNgX94JEuOAld2p0pwojrqLqL0lbSMWVCzy.VR8UJB96kE6u7.6a8IFwY0xPqfD8Fvt2PQ0Fhn1lUKIpOVNKiI.H0gTN4cjp9h6w2U5vM3NiPExjZWEk7SbyYlXtk1R7Lu0SnHHddz48u_6og2vxE2JW8hRkGs.eG6sABhlDWa2MJHXUNqz.fCCaR.tm3Dwn992cts0Q6lmjmjv9GF0JdskcC7EdIfKTV632Fxg90YOCavEZolecbcMX9vzKRtA.6ye3uYfCH_BS7FI4bZb4N9irls3yEGBiLGESkBQTIpqRdjCJcXQaEqeOfb_cFQer7gVPB6PKW4bJ27fFybzftlW7sHAPxCh0_yk6Scj_mogjqc3yakNlocca.eqZxdMLYETZ2zrnQs76vDLMWjPyC2xQ0vhorHZfBdE
   - `__cf_bm`

   > doesnt exist
   - Any other rows whose Domain column is exactly `queue-times.com` or `.queue-times.com`

For each one, copy the **Value** column. The values are long random strings.

## Step 3 — Get your User-Agent

Cloudflare binds `cf_clearance` to your exact User-Agent string. We need an exact match.

1. Still in DevTools, click the **Network** tab.
2. Refresh the page (Cmd+R).
3. Click any request in the list (the first one is usually the document).
4. Click **Headers** sub-tab.
5. Scroll down to **Request Headers** → find `User-Agent:`
6. Copy the entire value (one long string like `Mozilla/5.0 (Macintosh; ...) Chrome/...`)
> Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36
## Step 4 — Paste into a config file

Create the file `/Users/abghinav/Developer/epic-planner/scripts/qt_cookies.json` with this exact shape:

```json
{
  "user_agent": "PASTE YOUR User-Agent HERE",
  "cookies": {
    "cf_clearance": "PASTE cf_clearance VALUE HERE",
    "__cf_bm": "PASTE __cf_bm VALUE HERE",
    "uuid": "OPTIONAL: queue-times uuid value"
  }
}
```

You only **need** `cf_clearance` and `user_agent`. The others are bonus.

## Step 5 — Run the verifier

```sh
.venv/bin/python scripts/verify_cookies.py
```

If it prints "✓ cookies work — chart data found", we're good. We then run the full
backfill scraper which will take ~2-4 hours and produce real historical data for
every Epic Universe ride.

## Notes on cookie lifetime

- `cf_clearance` typically lasts ~30 min, but often longer if you visit other
  queue-times.com pages occasionally.
- If the scraper starts failing mid-run, re-do steps 1-4 to refresh cookies.
- `__cf_bm` rotates faster (~30 min). The scraper will pick up the latest from
  response headers automatically.
