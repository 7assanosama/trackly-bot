from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database import add_link, delete_link, get_user_links, get_user_plan, get_user_link_count, update_user_plan, get_stats, get_all_users
from utils import fetch_content
from lang import TEXTS
from config import ADMIN_ID

ADD_LINK, DELETE_LINK = range(2)

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
            [KeyboardButton(TEXTS[lang]["lang"]), KeyboardButton(TEXTS[lang]["plans"])],
            [KeyboardButton(TEXTS[lang]["help"])],
        ],
        resize_keyboard=True,
    )

# ================= UI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    await update.message.reply_text(
        TEXTS[lang]["menu"],
        reply_markup=build_menu(lang)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    msg = TEXTS[lang].get("help_message", TEXTS[lang]["help"])
    await update.message.reply_text(msg, reply_markup=build_menu(lang), parse_mode="Markdown")


async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    user_id = update.effective_chat.id
    msg = TEXTS[lang]["plans_info"].format(user_id=user_id)
    await update.message.reply_text(msg, reply_markup=build_menu(lang), parse_mode="Markdown")


# ================= ADMIN =================
async def set_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
        plan = context.args[1].lower()

        if plan not in ["free", "basic", "pro"]:
            raise ValueError()

        update_user_plan(user_id, plan)
        await update.message.reply_text(f"✅ User `{user_id}` upgraded to `{plan}` plan.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usage: `/set_plan <user_id> <free/basic/pro>`", parse_mode="Markdown")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("💎 ترقية حساب", callback_data="admin_upgrade")],
        [InlineKeyboardButton("📢 رسالة للجميع", callback_data="admin_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠️ **لوحة تحكم الإدارة:**", reply_markup=reply_markup, parse_mode="Markdown")


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ غير مصرح.", show_alert=True)
        return
        
    data = query.data
    await query.answer()

    if data == "admin_stats":
        users, links = get_stats()
        text = f"📊 **الإحصائيات الحالية:**\n\n👤 المستخدمين: {users}\n🔗 الروابط النشطة: {links}"
        await query.edit_message_text(text, parse_mode="Markdown")
        
    elif data == "admin_upgrade":
        text = "لترقية أي حساب، يرجى كتابة الأمر التالي:\n`/set_plan <user_id> <free/basic/pro>`\n\nمثال:\n`/set_plan 123456 pro`"
        await query.edit_message_text(text, parse_mode="Markdown")
        
    elif data == "admin_broadcast":
        text = "لإرسال رسالة لجميع المستخدمين، اكتب الأمر التالي متبوعاً بالرسالة:\n`/broadcast <رسالتك هنا>`"
        await query.edit_message_text(text, parse_mode="Markdown")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("❌ يجب كتابة الرسالة بعد الأمر.\nمثال: `/broadcast السلام عليكم`", parse_mode="Markdown")
        return

    users = get_all_users()
    count = 0
    for u_id in users:
        try:
            await context.bot.send_message(chat_id=u_id, text=f"📢 **رسالة إدارية:**\n\n{message}", parse_mode="Markdown")
            count += 1
        except Exception:
            pass

    await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {count} مستخدم.")


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
    user_id = update.effective_chat.id
    lang = get_lang(update, context)

    # Check Plan Limit
    user_plan = get_user_plan(user_id)
    links_count = get_user_link_count(user_id)
    
    limits = {"free": 1, "basic": 10}
    limit = limits.get(user_plan)

    if limit is not None and links_count >= limit:
        await update.message.reply_text(TEXTS[lang]["limit_reached"], reply_markup=build_menu(lang))
        return ConversationHandler.END

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
