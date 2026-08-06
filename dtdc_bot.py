"""
DTDC Shipment Tracker — Telegram Bot
-------------------------------------
Collects an AWB / Consignment number (and optionally a reference number)
from the user, then sends back a direct link to DTDC's official tracking
page along with the numbers to paste in.

NOTE ON THE CAPTCHA:
DTDC's tracking page uses a captcha specifically to prevent automated
bots from scraping it. This bot does NOT attempt to solve or bypass that
captcha — doing so would violate DTDC's terms of service and anti-bot
protections. Instead, the bot streamlines everything up to that point:
it collects your numbers via chat and gives you a one-tap link, so all
that's left for you to do is complete the captcha and view results.

Setup:
    pip install python-telegram-bot --upgrade

Run:
    export TELEGRAM_BOT_TOKEN="your-token-from-BotFather"
    python dtdc_bot.py
"""

import logging
import os
from urllib.parse import quote

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
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

# Conversation states
CHOOSING_METHOD, AWB_NUMBER, REF_NUMBER = range(3)

DTDC_TRACKING_URL = "https://www.dtdc.com/track-your-shipment/"

METHOD_AWB = "Track by AWB / Consignment No."
METHOD_REF = "Track by Reference No."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[METHOD_AWB], [METHOD_REF]]
    await update.message.reply_text(
        "📦 DTDC Shipment Tracker\n\n"
        "I'll help you look up a shipment. DTDC requires a captcha to be "
        "solved manually on their site, so I'll get everything ready and "
        "hand you a direct link — you just tap it and solve the captcha.\n\n"
        "How would you like to track?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSING_METHOD


async def choose_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == METHOD_AWB:
        await update.message.reply_text(
            "Enter your AWB / Consignment number:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return AWB_NUMBER
    elif choice == METHOD_REF:
        await update.message.reply_text(
            "Enter your Reference number:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return REF_NUMBER
    else:
        await update.message.reply_text("Please choose one of the options above.")
        return CHOOSING_METHOD


async def receive_awb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    awb = update.message.text.strip()
    context.user_data["awb"] = awb
    await send_tracking_link(update, context, awb=awb)
    return ConversationHandler.END


async def receive_ref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ref = update.message.text.strip()
    context.user_data["ref"] = ref
    await send_tracking_link(update, context, ref=ref)
    return ConversationHandler.END


async def send_tracking_link(
    update: Update, context: ContextTypes.DEFAULT_TYPE, awb: str = None, ref: str = None
) -> None:
    lines = ["✅ Ready to track!\n"]
    if awb:
        lines.append(f"AWB / Consignment No.: `{awb}`")
    if ref:
        lines.append(f"Reference No.: `{ref}`")

    lines.append(
        f"\n1️⃣ Tap the link below\n"
        f"2️⃣ Paste the number above into the tracking field\n"
        f"3️⃣ Solve the captcha shown on DTDC's page\n\n"
        f"🔗 {DTDC_TRACKING_URL}"
    )

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", disable_web_page_preview=False
    )
    await update.message.reply_text(
        "Use /track to look up another shipment anytime."
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Cancelled.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/track — start tracking a shipment\n"
        "/cancel — cancel the current lookup\n"
        "/help — show this message"
    )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Set the TELEGRAM_BOT_TOKEN environment variable before running."
        )

    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("track", start), CommandHandler("start", start)],
        states={
            CHOOSING_METHOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_method)
            ],
            AWB_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_awb)
            ],
            REF_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ref)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
