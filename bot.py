from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from aiohttp import web
import asyncio
import os

from config import BOT_TOKEN
from database import add_link, delete_link, get_user_links
from utils import fetch_content
from monitor import start_monitor

# ================== CONFIG ==================
WEBHOOK_BASE = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", 8080))

# ================== UI ==================
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ إضافة رابط")],
        [KeyboardButton("📁 عرض الروابط"), KeyboardButton("🗑️ حذف رابط")],
        [KeyboardButton("ℹ️ مساعدة")],
    ],
    resize_keyboard=True,
)

ADD_LINK, DELETE_LINK = range(2)

MENU_TEXT = (
    "مرحبا بك في Trackly Bot!\n"
    "Trackly بيخليك تراقب أي موقع ويب بسهولة ويبلغك أول ما يحصل تغيير.\n\n"
    "الأوامر المتاحة:\n"
    "🔹 /help — عرض هذه القائمة التفصيلية.\n"
    "🔹 /list — عرض الروابط اللي بتراقبها حاليا.\n"
    "🔹 /delete <الرابط> — حذف الرابط من المراقبة.\n\n"
    "لإضافة رابط جديد، ابعته مباشرة في المحادثة."
)

# ================== HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MENU_TEXT, reply_markup=MAIN_MENU)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 دليل استخدام Trackly Bot:\n\n"
        "• اضغط على زر ➕ إضافة رابط لإضافة رابط جديد للمراقبة.\n"
        "• اضغط على زر 📁 عرض الروابط لعرض ما تراقبه الآن.\n"
        "• اضغط على زر 🗑️ حذف رابط لحذف رابط من المراقبة.\n"
        "• اضغط على /cancel لإلغاء أي عملية.",
        reply_markup=MAIN_MENU,
    )


async def prompt_add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ابعتلي الرابط:", reply_markup=ReplyKeyboardRemove())
    return ADD_LINK


async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.chat_id

    content = fetch_content(url)
    if not content:
        await update.message.reply_text("❌ اللينك مش شغال، حاول تاني أو /cancel")
        return ADD_LINK

    add_link(user_id, url, content)
    await update.message.reply_text("✅ تم الإضافة", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def prompt_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ابعت اللينك اللي عايز تحذفه:", reply_markup=ReplyKeyboardRemove())
    return DELETE_LINK


async def receive_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    url = update.message.text

    removed = delete_link(user_id, url)
    if removed:
        await update.message.reply_text("✅ تم الحذف", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("❌ مش موجود", reply_markup=MAIN_MENU)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    links = get_user_links(user_id)

    if not links:
        await update.message.reply_text("مافيش لينكات")
        return

    text = "📁 روابطك:\n"
    for link in links:
        _, _, url, _ = link
        text += f"- {url}\n"

    await update.message.reply_text(text)


async def delete_link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    url = " ".join(context.args).strip()

    if not url:
        await update.message.reply_text("اكتب /delete <link>")
        return

    removed = delete_link(user_id, url)
    if removed:
        await update.message.reply_text("✅ تم الحذف", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("❌ مش موجود", reply_markup=MAIN_MENU)


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم الأزرار 👇", reply_markup=MAIN_MENU)


# ================== BACKGROUND ==================
async def post_init(app):
    asyncio.create_task(start_monitor(app.bot))


# ================== WEBHOOK ==================
async def webhook_handler(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="ok")


async def main():
    await app.initialize()

    # حذف أي webhook قديم
    await app.bot.delete_webhook(drop_pending_updates=True)

    # تسجيل الجديد
    await app.bot.set_webhook(WEBHOOK_URL)

    # سيرفر
    web_app = web.Application()
    web_app.router.add_post(WEBHOOK_PATH, webhook_handler)

    runner = web.AppRunner(web_app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print("🚀 Webhook running...")

    await app.start()
    await asyncio.Event().wait()


# ================== RUN ==================
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_links))
    app.add_handler(CommandHandler("delete", delete_link_cmd))

    app.add_handler(ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ إضافة رابط$"), prompt_add_link),
            MessageHandler(filters.Regex("^🗑️ حذف رابط$"), prompt_delete_link),
        ],
        states={
            ADD_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
            DELETE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    app.add_handler(MessageHandler(filters.Regex("^📁 عرض الروابط$"), list_links))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ مساعدة$"), help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

    print("Bot is starting...")

    asyncio.run(main())