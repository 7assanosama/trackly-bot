from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import threading

from config import BOT_TOKEN
from database import add_link
from utils import fetch_content
from monitor import start_monitor


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ابعتلي أي لينك وانا هراقبه ليك 👀")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.chat_id

    content = fetch_content(url)

    if not content:
        await update.message.reply_text("❌ مش قادر اقرأ اللينك")
        return

    add_link(user_id, url, content)
    await update.message.reply_text("✅ تم إضافة اللينك للمراقبة")


def run_monitor(app):
    start_monitor(app.bot)


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    # تشغيل المونيتور في Thread
    threading.Thread(target=run_monitor, args=(app,), daemon=True).start()

    print("Bot is running...")
    app.run_polling()