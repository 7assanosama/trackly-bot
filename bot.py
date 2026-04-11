from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import threading

from config import BOT_TOKEN
from database import add_link, delete_link, get_user_links
from utils import fetch_content
from monitor import start_monitor

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
    await update.message.reply_text(
        "ابعتلي الرابط اللي عايز تراقبه:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ADD_LINK


async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.chat_id

    content = fetch_content(url)
    if not content:
        await update.message.reply_text("❌ مش قادر اقرأ اللينك، حاول مرة تانية أو اضغط /cancel.")
        return ADD_LINK

    add_link(user_id, url, content)
    await update.message.reply_text("✅ تم إضافة اللينك للمراقبة", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def prompt_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ابعتلي الرابط اللي عايز تحذفه:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DELETE_LINK


async def receive_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    url = update.message.text

    removed = delete_link(user_id, url)
    if removed:
        await update.message.reply_text("✅ تم حذف اللينك من المراقبة", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("❌ مش لقيت اللينك ده في المراقبة", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    links = get_user_links(user_id)

    if not links:
        await update.message.reply_text("مافيش لينكات مراقبة دلوقتي.")
        return

    text = "اللينكات اللي بترقبها:\n"
    for link in links:
        link_id, _, url, _ = link
        text += f"- {url}\n"

    await update.message.reply_text(text)


async def delete_link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    url = " ".join(context.args).strip()

    if not url:
        await update.message.reply_text("اكتب /delete <اللنك> علشان احذفه.")
        return

    removed = delete_link(user_id, url)
    if removed:
        await update.message.reply_text("✅ تم حذف اللينك من المراقبة", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("❌ مش لقيت اللينك ده في المراقبة", reply_markup=MAIN_MENU)


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "من فضلك استخدم الأزرار في القائمة لإدارة البوت.",
        reply_markup=MAIN_MENU,
    )


# ✅ دي الحركة الصح
async def post_init(app):
    import asyncio
    asyncio.create_task(start_monitor(app.bot))


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

    print("Bot is running...")
    app.run_polling()
