from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)
from aiohttp import web
import asyncio
import os

from config import BOT_TOKEN
from monitor import start_monitor
from handlers import *

# ================= CONFIG =================
BASE_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"


# ================= WEBHOOK APP =================
application = ApplicationBuilder().token(BOT_TOKEN).build()


# ================= WEBHOOK HANDLER =================
async def webhook_handler(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)

    # ✔️ correct way (safe with PTB async)
    await application.update_queue.put(update)

    return web.Response(text="ok")


# ================= MAIN =================
async def main():
    await application.initialize()

    # Start monitor task directly
    asyncio.create_task(start_monitor(application))

    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(url=WEBHOOK_URL)

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
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my", my_command))
    application.add_handler(CommandHandler("set_limit", set_limit_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    application.add_handler(
        MessageHandler(filters.Regex("^(🌐 تغيير اللغة|🌐 Language)$"), change_lang)
    )
    application.add_handler(
        MessageHandler(filters.Regex("^(🇸🇦 العربية|🇬🇧 English)$"), set_lang)
    )
    application.add_handler(
        MessageHandler(filters.Regex("^(ℹ️ الدعم|ℹ️ support)$"), help_command)
    )
    application.add_handler(
        MessageHandler(filters.Regex("^(👤 حسابي|👤 My Account)$"), my_command)
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^(💎 خطط التسعير|💎 Pricing Plans)$"), plans_command
        )
    )
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("add", prompt_add_link),
            MessageHandler(
                filters.Regex("^(➕ إضافة رابط|➕ Add link)$"), prompt_add_link
            ),
            CommandHandler("delete", prompt_delete_link),
            MessageHandler(
                filters.Regex("^(🗑️ حذف رابط|🗑️ Delete link)$"), prompt_delete_link
            ),
            CommandHandler("list", list_links),
            MessageHandler(filters.Regex("^(📁 عرض الروابط|📁 My links)$"), list_links),
        ],
        states={
            ADD_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
            DELETE_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv)

    print("Bot starting...")

    asyncio.run(main())
