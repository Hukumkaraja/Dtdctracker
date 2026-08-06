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

Runs as a **Docker** deploy on Render, using Playwright's official base
image (Chromium + all system libraries pre-installed) — this avoids the
apt/sudo permission issues that break `playwright install --with-deps`
on Render's standard Python build environment.

## Local setup (optional, for testing before deploying)

### 1. Create a Telegram bot
- Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token

### 2. Build and run the Docker image locally
```bash
docker build -t dtdc-bot .
docker run -e TELEGRAM_BOT_TOKEN="your-token-here" -p 10000:10000 dtdc-bot
```

### 3. Use it
In Telegram: `/track` → send your AWB → bot sends the captcha image →
type the answer → bot sends back a screenshot of your result.

## Deploying on Render (Docker)

1. Push all 4 files to your GitHub repo: `dtdc_bot.py`, `requirements.txt`,
   `Dockerfile`, `README.md`
2. On Render, go to your existing service → **Settings**
3. Under **Build & Deploy**, change **Environment** from "Python" to
   **Docker** (Render auto-detects the `Dockerfile` in your repo root)
4. Under **Environment**, make sure `TELEGRAM_BOT_TOKEN` is still set
   (it should carry over, but double-check)
5. Save → Render will rebuild using the Dockerfile this time
6. Watch **Logs** — you want to see `Bot starting...` with no errors

If Render doesn't offer an "Environment" toggle on your existing
service, it's sometimes simpler to delete the old service and create a
fresh one: **New + → Web Service** → connect your repo → Render will
detect the `Dockerfile` automatically and use it without you needing to
set a Build/Start command manually.

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
6. Commit and push — Render will rebuild automatically

## Limitations to expect
- If DTDC changes their page layout, selectors will need updating again
- Captchas can expire after a minute or two — if submission fails, just
  `/track` again for a fresh one
- Multiple people using the bot at once means multiple Chromium browser
  instances running simultaneously — fine for personal use, but heavier
  usage would need more RAM than Render's free tier gives
- The free tier still sleeps after ~15 min idle, so the first message
  after a quiet period takes 30–60s to wake up
