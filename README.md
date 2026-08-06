# DTDC Shipment Tracker — Telegram Bot

A Telegram bot that collects your AWB / Consignment number or Reference
number via chat, then hands you a direct link to DTDC's official tracking
page so you can finish the lookup in one tap.

## Why it's semi-automated, not fully automated

DTDC's tracking page requires a captcha to be solved by a human. This is
an anti-bot measure, and this bot does not attempt to bypass or auto-fill
it — that would violate DTDC's terms of service. Instead, the bot
automates everything else: collecting your number(s) and generating the
link, so solving the captcha is the only manual step left.

## Setup

1. **Create a bot with BotFather**
   - Open Telegram, message [@BotFather](https://t.me/BotFather)
   - Send `/newbot` and follow the prompts
   - Copy the token it gives you

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your token**
   ```bash
   export TELEGRAM_BOT_TOKEN="123456:ABC-your-token-here"
   ```

4. **Run the bot**
   ```bash
   python dtdc_bot.py
   ```

5. In Telegram, message your bot `/track` and follow the prompts.

## Commands

- `/track` — start a new shipment lookup
- `/cancel` — cancel the current lookup
- `/help` — show available commands

## Deploying so it runs 24/7

Locally running `python dtdc_bot.py` only works while your machine is on.
For always-on hosting, consider:
- A small VPS (e.g. a $5/mo box) running the script under `systemd` or `tmux`
- Render.com / Railway.app "worker" service (free/cheap tiers)
- A Raspberry Pi at home

## Extending this bot

If you later get access to DTDC's official Business/API tracking service
(no captcha required for API partners), this bot can be upgraded to call
that API directly and return live status inline — just let me know and
I can wire that in.
