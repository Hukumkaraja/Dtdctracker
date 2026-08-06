"""
DTDC Shipment Tracker — Telegram Bot (browser-automation version)
-------------------------------------------------------------------
Flow:
  1. User sends /track, then their AWB / Consignment number.
  2. Bot opens a real (headless) browser, goes to DTDC's tracking page,
     and fills in the AWB field automatically.
  3. Bot crops out just the captcha image and sends it to the user as a
     photo in Telegram.
  4. User reads the captcha and types the answer back as a normal message.
  5. Bot types that answer into the captcha field, submits the form, and
     sends back a screenshot of the result.

IMPORTANT — WHY THIS DOESN'T BYPASS THE CAPTCHA:
The captcha itself is still solved by a human (you) every time. The bot
only automates the mechanical parts around it (typing the AWB, cropping
the image, clicking submit) — it never reads, solves, or auto-fills the
captcha answer itself. That's a deliberate line: DTDC's captcha exists to
require a human in the loop, and this bot keeps a human in the loop.

IMPORTANT — SELECTORS MAY NEED ADJUSTING:
DTDC's page structure isn't something I could inspect directly while
writing this (their robots.txt blocks automated fetching of the page
even just to look at it). The selectors below are my best guess based on
common patterns for tracking forms. If the bot can't find a field, use
/debug_screenshot to get a full-page image, then open DTDC's tracking
page in your own browser, right-click the AWB field / captcha image /
submit button, choose "Inspect", and update the SELECTORS dict below
with the actual id/name/class you see.

Setup:
    pip install -r requirements.txt
    playwright install chromium --with-deps

Run:
    export TELEGRAM_BOT_TOKEN="your-token-from-BotFather"
    python dtdc_bot.py
"""

import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DTDC_TRACKING_URL = "https://www.dtdc.com/track-your-shipment/"

# ---------------------------------------------------------------------
# ADJUST THESE if the bot can't find a field on DTDC's actual page.
# Each entry is a list of candidate CSS selectors tried in order.
# ---------------------------------------------------------------------
SELECTORS = {
    "awb_input": [
        "input[name='trackingId']",
        "input[id*='awb' i]",
        "input[placeholder*='AWB' i]",
        "input[placeholder*='consignment' i]",
        "input[name*='tracking' i]",
    ],
    "captcha_image": [
        "img[id*='captcha' i]",
        "img[class*='captcha' i]",
        "img[src*='captcha' i]",
    ],
    "captcha_input": [
        "input[id*='captcha' i]",
        "input[name*='captcha' i]",
        "input[placeholder*='captcha' i]",
    ],
    "submit_button": [
        "button[type='submit']",
        "button[id*='track' i]",
        "button:has-text('Track')",
        "input[type='submit']",
    ],
    "results_container": [
        "[id*='result' i]",
        "[class*='result' i]",
        "[class*='tracking-status' i]",
        "[class*='shipment-detail' i]",
    ],
}

# chat_id -> {"browser":..., "page":..., "playwright":..., "awb": str}
SESSIONS: dict = {}

AWB_NUMBER, CAPTCHA_ANSWER = range(2)


async def _first_match(page, selector_list):
    """Return the first Locator from selector_list that exists on the page."""
    for sel in selector_list:
        loc = page.locator(sel).first
        try:
            await loc.wait_for(state="attached", timeout=3000)
            return loc
        except PWTimeout:
            continue
    return None


async def _close_session(chat_id: int) -> None:
    session = SESSIONS.pop(chat_id, None)
    if not session:
        return
    try:
        await session["browser"].close()
        await session["playwright"].stop()
    except Exception:
        pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📦 DTDC Shipment Tracker\n\n"
        "Send me your AWB / Consignment number. I'll fill it in on DTDC's "
        "page and send you just the captcha image to solve — you type the "
        "answer back to me and I'll submit it and get your result.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return AWB_NUMBER


async def receive_awb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    awb = update.message.text.strip()
    await update.message.reply_text("🔎 Opening DTDC's page and filling in your AWB...")

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
        await page.goto(DTDC_TRACKING_URL, timeout=30000, wait_until="domcontentloaded")

        awb_field = await _first_match(page, SELECTORS["awb_input"])
        if not awb_field:
            raise RuntimeError(
                "Couldn't find the AWB input field. Try /debug_screenshot "
                "to see the page and update SELECTORS['awb_input'] in the code."
            )
        await awb_field.fill(awb)

        captcha_img = await _first_match(page, SELECTORS["captcha_image"])
        if not captcha_img:
            raise RuntimeError(
                "Couldn't find the captcha image. Try /debug_screenshot "
                "to see the page and update SELECTORS['captcha_image'] in the code."
            )

        screenshot_path = f"/tmp/captcha_{chat_id}.png"
        await captcha_img.screenshot(path=screenshot_path)

        SESSIONS[chat_id] = {
            "browser": browser,
            "page": page,
            "playwright": pw,
            "awb": awb,
        }

        with open(screenshot_path, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption="Type what you see in this captcha image:",
            )
        return CAPTCHA_ANSWER

    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")
        await browser.close()
        await pw.stop()
        return ConversationHandler.END


async def receive_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    session = SESSIONS.get(chat_id)
    if not session:
        await update.message.reply_text(
            "That session expired — send /track to start again."
        )
        return ConversationHandler.END

    page = session["page"]
    captcha_text = update.message.text.strip()
    await update.message.reply_text("📨 Submitting...")

    try:
        captcha_field = await _first_match(page, SELECTORS["captcha_input"])
        if not captcha_field:
            raise RuntimeError(
                "Couldn't find the captcha input field. Update "
                "SELECTORS['captcha_input'] in the code."
            )
        await captcha_field.fill(captcha_text)

        submit_btn = await _first_match(page, SELECTORS["submit_button"])
        if not submit_btn:
            raise RuntimeError(
                "Couldn't find the submit button. Update "
                "SELECTORS['submit_button'] in the code."
            )
        await submit_btn.click()

        await page.wait_for_timeout(3000)  # let results render

        results = await _first_match(page, SELECTORS["results_container"])
        screenshot_path = f"/tmp/result_{chat_id}.png"
        if results:
            await results.screenshot(path=screenshot_path)
        else:
            await page.screenshot(path=screenshot_path, full_page=True)

        with open(screenshot_path, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=f"Result for AWB {session['awb']}. "
                "If the captcha was wrong, send /track to try again.",
            )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ {e}\n\nSend /track to try again — captchas sometimes expire "
            "or the answer may have been mistyped."
        )
    finally:
        await _close_session(chat_id)

    return ConversationHandler.END


async def debug_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Utility command: opens DTDC's page fresh and sends a full-page
    screenshot so you can inspect real field names/classes yourself."""
    await update.message.reply_text("📸 Taking a full-page screenshot...")
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    try:
        await page.goto(DTDC_TRACKING_URL, timeout=30000, wait_until="domcontentloaded")
        path = f"/tmp/debug_{update.effective_chat.id}.png"
        await page.screenshot(path=path, full_page=True)
        with open(path, "rb") as f:
            await update.message.reply_photo(photo=f)
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")
    finally:
        await browser.close()
        await pw.stop()


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _close_session(update.effective_chat.id)
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/track — start tracking a shipment\n"
        "/cancel — cancel the current lookup\n"
        "/debug_screenshot — see the raw DTDC page (for fixing selectors)\n"
        "/help — show this message"
    )


class _HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"DTDC Telegram bot is running.")

    def log_message(self, format, *args):
        pass


def _run_health_server() -> None:
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), _HealthCheckHandler)
    logger.info(f"Health check server listening on port {port}")
    server.serve_forever()


def main() -> None:
    threading.Thread(target=_run_health_server, daemon=True).start()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Set the TELEGRAM_BOT_TOKEN environment variable before running."
        )

    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("track", start), CommandHandler("start", start)],
        states={
            AWB_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_awb)
            ],
            CAPTCHA_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_captcha)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("debug_screenshot", debug_screenshot))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
