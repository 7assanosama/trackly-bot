from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database import add_link, delete_link, get_user_links, get_user_plan, get_user_link_count, update_user_plan, get_stats, get_all_users, get_users_info
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
            [KeyboardButton(TEXTS[lang]["my_account"]), KeyboardButton(TEXTS[lang]["help"])],
        ],
        resize_keyboard=True,
    )

# ================= UI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    user_id = update.effective_chat.id
    get_user_plan(user_id) # Save user to DB if not exists
    await update.message.reply_text(
        TEXTS[lang]["menu"],
        reply_markup=build_menu(lang)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    msg = TEXTS[lang].get("help_message", TEXTS[lang]["help"])
    await update.message.reply_text(msg, reply_markup=build_menu(lang), parse_mode="Markdown")


async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    user_id = update.effective_user.id
    user_plan = get_user_plan(user_id)
    plan_map = {"free": TEXTS[lang]["plan_free"], "basic": TEXTS[lang]["plan_basic"], "pro": TEXTS[lang]["plan_pro"]}
    plan_text = plan_map.get(user_plan, user_plan)
    msg = TEXTS[lang]["my_account_info"].format(user_id=user_id, plan_text=plan_text)
    await update.message.reply_text(msg, parse_mode="Markdown")


async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    user_id = update.effective_chat.id
    msg = TEXTS[lang]["plans_info"].format(user_id=user_id)
    await update.message.reply_text(msg, reply_markup=build_menu(lang), parse_mode="Markdown")


# ================= ADMIN =================
async def set_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    lang = get_lang(update, context)
    try:
        user_id = int(context.args[0])
        plan = context.args[1].lower()

        if plan not in ["free", "basic", "pro"]:
            raise ValueError()

        update_user_plan(user_id, plan)
        msg = TEXTS[lang]["admin_plan_upgraded"].format(user_id=user_id, plan=plan)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except (IndexError, ValueError):
        await update.message.reply_text(TEXTS[lang]["admin_plan_usage"], parse_mode="Markdown")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    lang = get_lang(update, context)
    keyboard = [
        [InlineKeyboardButton(TEXTS[lang]["admin_btn_stats"], callback_data="admin_stats")],
        [InlineKeyboardButton(TEXTS[lang]["admin_btn_users"], callback_data="admin_users")],
        [InlineKeyboardButton(TEXTS[lang]["admin_btn_upgrade"], callback_data="admin_upgrade")],
        [InlineKeyboardButton(TEXTS[lang]["admin_btn_broadcast"], callback_data="admin_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(TEXTS[lang]["admin_panel"], reply_markup=reply_markup, parse_mode="Markdown")


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = get_lang(update, context)
    if query.from_user.id != ADMIN_ID:
        await query.answer(TEXTS[lang]["admin_unauthorized"], show_alert=True)
        return
        
    data = query.data
    await query.answer()

    if data == "admin_stats":
        users, links = get_stats()
        text = TEXTS[lang]["admin_stats_msg"].format(users=users, links=links)
        await query.edit_message_text(text, parse_mode="Markdown")
        
    elif data == "admin_users":
        users_info = get_users_info()
        text = TEXTS[lang]["admin_users_title"]
        for uid, plan, count in users_info:
            plan_map = {"free": TEXTS[lang]["plan_free"], "basic": TEXTS[lang]["plan_basic"], "pro": TEXTS[lang]["plan_pro"]}
            p_text = plan_map.get(plan, plan)
            text += TEXTS[lang]["admin_users_row"].format(user_id=uid, plan=p_text, count=count)
        
        if len(text) > 4000:
            text = text[:4000] + "\n... (المزيد / More)"
            
        await query.edit_message_text(text, parse_mode="Markdown")
        
    elif data == "admin_upgrade":
        text = TEXTS[lang]["admin_upgrade_msg"]
        await query.edit_message_text(text, parse_mode="Markdown")
        
    elif data == "admin_broadcast":
        text = TEXTS[lang]["admin_broadcast_msg"]
        await query.edit_message_text(text, parse_mode="Markdown")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    lang = get_lang(update, context)
    
    # تسجيل المشرف تلقائياً في قاعدة البيانات ليصله البث
    get_user_plan(update.effective_chat.id)
    
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text(TEXTS[lang]["broadcast_usage"], parse_mode="Markdown")
        return

    users = get_all_users()
    count = 0
    failed = 0
    prefix = TEXTS[lang]["broadcast_prefix"].format(message=message)
    for u_id in users:
        try:
            await context.bot.send_message(chat_id=u_id, text=prefix)
            count += 1
        except Exception as e:
            print(f"Failed to send to {u_id}: {e}")
            failed += 1

    msg = TEXTS[lang]["broadcast_sent"].format(count=count)
    if failed > 0:
        msg += f"\n❌ فشل الإرسال إلى {failed} مستخدم."
    await update.message.reply_text(msg)


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

    await update.message.reply_text(TEXTS[lang]["send_add_link"], reply_markup=ReplyKeyboardRemove())
    return ADD_LINK


async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.effective_chat.id
    lang = get_lang(update, context)

    if url.strip().lower() in ["cancel", "الغاء", "إلغاء"]:
        return await cancel(update, context)

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

    if url.strip().lower() in ["cancel", "الغاء", "إلغاء"]:
        return await cancel(update, context)

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
