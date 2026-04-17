from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database import add_link, delete_link, get_user_links, get_user_plan, get_user_link_count
from utils import fetch_content
from lang import TEXTS

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
    await update.message.reply_text(TEXTS[lang]["plans_info"], reply_markup=build_menu(lang), parse_mode="Markdown")


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
