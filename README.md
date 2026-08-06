# DTDC Shipment Tracker — Telegram Bot (browser-automation version)

Fully free, no paid API. The bot opens a real browser, fills in your AWB
number on DTDC's own tracking page, and sends you *just the captcha
image* inside Telegram. You type the answer back as a normal message —
the bot submits it and sends you a screenshot of the result. You never
open a browser yourself.

**Note on the captcha:** the bot never reads or solves it — you always
do that part. That's intentional: it keeps a human in the loop, which is
what DTDC's captcha is there to require. Everything else (typing the
AWB, cropping the captcha image, clicking submit) is automated.

## Setup

### 1. Create a Telegram bot
- Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token

### 2. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium --with-deps
```
(The `--with-deps` flag installs system libraries Chromium needs — on
Render this happens automatically during the build step below.)

### 3. Set your token
```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-your-token-here"
```

### 4. Run
```bash
python dtdc_bot.py
```

### 5. Use it
`/track` → send your AWB → bot sends you the captcha image → type the
answer → bot sends back a screenshot of your tracking result.

## Commands
- `/track` — start a lookup
- `/cancel` — cancel the current lookup
- `/debug_screenshot` — full-page screenshot of DTDC's tracking page,
  useful if a field can't be found (see below)
- `/help` — show commands

## If the bot can't find a field ("Couldn't find the AWB input field" etc.)

I wrote the CSS selectors in `dtdc_bot.py` (the `SELECTORS` dictionary
near the top) based on common patterns for tracking forms, since I
couldn't fetch DTDC's actual page myself while building this (their
robots.txt blocks that). If a selector doesn't match:

1. Send `/debug_screenshot` to see the real page
2. Open https://www.dtdc.com/track-your-shipment/ yourself in Chrome
3. Right-click the AWB field (or captcha image, or submit button) →
   **Inspect**
4. Note the `id`, `name`, or `class` attribute shown in dev tools
5. Add it to the matching list in `SELECTORS` in `dtdc_bot.py`, e.g.:
   ```python
   "awb_input": [
       "input#the-real-id-you-found",   # add this line
       "input[name='trackingId']",
       ...
   ],
   ```
6. Redeploy

## Deploying on Render

Chromium is memory-heavy. Render's **free** Web Service tier (512 MB
RAM) may be too tight to run headless Chromium reliably — expect
possible crashes or slow page loads. If you hit that, upgrading to the
**Starter** instance ($7/mo, 512 MB→ more headroom depending on plan) or
a small VPS will be much more stable. Steps either way:

1. Push these files to a GitHub repo
2. Render dashboard → **New + → Web Service** → connect the repo
3. Build command: `pip install -r requirements.txt && playwright install chromium --with-deps`
4. Start command: `python dtdc_bot.py`
5. Add environment variable: `TELEGRAM_BOT_TOKEN`
6. Deploy — check Logs for `Bot starting...`

On the free tier, the service also sleeps after ~15 min idle, so the
first message after a quiet period takes 30–60s to wake up.

## Limitations to expect
- If DTDC changes their page layout, selectors will need updating again
- Captchas can expire after a minute or two — if submission fails, just
  `/track` again for a fresh one
- Multiple people using the bot at once means multiple Chromium browser
  instances running simultaneously, which needs more RAM than a single
  free-tier instance may have
