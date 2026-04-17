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
BASE_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

ADD_LINK, DELETE_LINK = range(2)

# ================= LANG SYSTEM =================
TEXTS = {
    "ar": {
        "menu": "مرحبا بك في Trackly Bot 🚀",
        "add_link": "➕ إضافة رابط",
        "list_links": "📁 عرض الروابط",
        "delete_link": "🗑️ حذف رابط",
        "help": "ℹ️ مساعدة",
        "send_link": "ابعت الرابط:",
        "invalid_url": "❌ رابط غير صالح",
        "added": "✅ تم الإضافة",
        "deleted": "تم الحذف",
        "no_links": "لا يوجد روابط",
        "links_title": "📁 روابطك:",
        "cancel": "تم الإلغاء",
        "lang": "🌐 تغيير اللغة",
        "choose_lang": "اختر اللغة:",
    },
    "en": {
        "menu": "Welcome to Trackly Bot 🚀",
        "add_link": "➕ Add link",
        "list_links": "📁 My links",
        "delete_link": "🗑️ Delete link",
        "help": "ℹ️ Help",
        "send_link": "Send the link:",
        "invalid_url": "❌ Invalid URL",
        "added": "✅ Added successfully",
        "deleted": "Deleted",
        "no_links": "No links found",
        "links_title": "📁 Your links:",
        "cancel": "Cancelled",
        "lang": "🌐 Language",
        "choose_lang": "Choose language:",
    }
}

def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_lang = context.user_data.get("lang")

    if user_lang:
        return user_lang

    tg_lang = update.effective_user.language_code or "en"
    return "ar" if tg_lang.startswith("ar") else "en"


def t(update, context, key):
    lang = get_lang(update, context)
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)


def build_menu(lang: str):
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(TEXTS[lang]["add_link"])],
            [KeyboardButton(TEXTS[lang]["list_links"]), KeyboardButton(TEXTS[lang]["delete_link"])],
            [KeyboardButton(TEXTS[lang]["lang"]), KeyboardButton(TEXTS[lang]["help"])],
        ],
        resize_keyboard=True,
    )

# ================= APP =================
application = ApplicationBuilder().token(BOT_TOKEN).build()

# ================= UI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    await update.message.reply_text(
        TEXTS[lang]["menu"],
        reply_markup=build_menu(lang)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    await update.message.reply_text(TEXTS[lang]["help"], reply_markup=build_menu(lang))


# ================= LANGUAGE =================
async def change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🇸🇦 العربية"), KeyboardButton("🇬🇧 English")]
    ]

    lang = get_lang(update, context)

    await update.message.reply_text(
        TEXTS[lang]["choose_lang"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "العربية" in text:
        context.user_data["lang"] = "ar"
    elif "English" in text:
        context.user_data["lang"] = "en"

    lang = get_lang(update, context)

    await update.message.reply_text(
        TEXTS[lang]["menu"],
        reply_markup=build_menu(lang)
    )

# ================= LINKS =================
async def prompt_add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    await update.message.reply_text(TEXTS[lang]["send_link"], reply_markup=ReplyKeyboardRemove())
    return ADD_LINK


async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.effective_chat.id
    lang = get_lang(update, context)

    content = fetch_content(url)
    if not content:
        await update.message.reply_text(TEXTS[lang]["invalid_url"])
        return ADD_LINK

    add_link(user_id, url, content)
    await update.message.reply_text(TEXTS[lang]["added"], reply_markup=build_menu(lang))
    return ConversationHandler.END


async def prompt_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    await update.message.reply_text(TEXTS[lang]["send_link"], reply_markup=ReplyKeyboardRemove())
    return DELETE_LINK


async def receive_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    url = update.message.text
    lang = get_lang(update, context)

    delete_link(user_id, url)
    await update.message.reply_text(TEXTS[lang]["deleted"], reply_markup=build_menu(lang))
    return ConversationHandler.END


async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    lang = get_lang(update, context)

    links = get_user_links(user_id)

    if not links:
        await update.message.reply_text(TEXTS[lang]["no_links"])
        return

    text = TEXTS[lang]["links_title"] + "\n"
    for _, _, url, _ in links:
        text += f"- {url}\n"

    await update.message.reply_text(text)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    await update.message.reply_text(TEXTS[lang]["cancel"], reply_markup=build_menu(lang))
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


# ================= MAIN =================
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

    application.add_handler(MessageHandler(filters.Regex("^🌐 تغيير اللغة$"), change_lang))
    application.add_handler(MessageHandler(filters.Regex("^(🇸🇦 العربية|🇬🇧 English)$"), set_lang))

    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ إضافة رابط$"), prompt_add_link),
            MessageHandler(filters.Regex("^🗑️ حذف رابط$"), prompt_delete_link),
            MessageHandler(filters.Regex("^📁 عرض الروابط$"), list_links),
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