from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from aiohttp import web
import asyncio
import os

from config import BOT_TOKEN
from database import add_link, delete_link, get_user_links
from utils import fetch_content
from monitor import start_monitor

# ================= CONFIG =================
BASE_URL = os.getenv("WEBHOOK_URL")  # https://xxxx.up.railway.app
PORT = int(os.getenv("PORT", 8080))

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# ================= APP =================
application = ApplicationBuilder().token(BOT_TOKEN).build()

ADD_LINK, DELETE_LINK = range(2)

# ================= UI =================
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ إضافة رابط")],
        [KeyboardButton("📁 عرض الروابط"), KeyboardButton("🗑️ حذف رابط")],
        [KeyboardButton("ℹ️ مساعدة")],
    ],
    resize_keyboard=True,
)

MENU_TEXT = "مرحبا بك في Trackly Bot 🚀"

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MENU_TEXT, reply_markup=MAIN_MENU)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم الأزرار 👇", reply_markup=MAIN_MENU)

async def prompt_add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ابعت الرابط:", reply_markup=ReplyKeyboardRemove())
    return ADD_LINK

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.effective_chat.id

    content = fetch_content(url)
    if not content:
        await update.message.reply_text("❌ رابط غير صالح")
        return ADD_LINK

    add_link(user_id, url, content)
    await update.message.reply_text("✅ تم الإضافة", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def prompt_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ابعت الرابط:", reply_markup=ReplyKeyboardRemove())
    return DELETE_LINK

async def receive_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    url = update.message.text

    delete_link(user_id, url)
    await update.message.reply_text("تم الحذف", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    links = get_user_links(user_id)

    if not links:
        await update.message.reply_text("لا يوجد روابط")
        return

    text = "📁 روابطك:\n"
    for _, _, url, _ in links:
        text += f"- {url}\n"

    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# ================= MONITOR =================
async def post_init(app):
    asyncio.create_task(start_monitor(app.bot))

# ================= WEBHOOK =================
async def webhook_handler(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response(text="ok")

# ================= STARTUP =================
async def main():
    await application.initialize()

    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(WEBHOOK_URL)

    aio_app = web.Application()
    aio_app.router.add_post(WEBHOOK_PATH, webhook_handler)

    runner = web.AppRunner(aio_app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print("🚀 Bot is running on webhook")

    await application.start()
    await asyncio.Event().wait()

# ================= RUN =================
if __name__ == "__main__":
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_links))

    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ إضافة رابط$"), prompt_add_link),
            MessageHandler(filters.Regex("^🗑️ حذف رابط$"), prompt_delete_link),
        ],
        states={
            ADD_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
            DELETE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv)

    print("Bot starting...")

    asyncio.run(main())