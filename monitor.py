import asyncio
import difflib
from database import get_links, update_content
from utils import fetch_content
from config import CHECK_INTERVAL
from lang import TEXTS


def get_diff(old, new, lang_dict):
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        lineterm="",
        fromfile=lang_dict["diff_before"],
        tofile=lang_dict["diff_after"]
    )
    return "\n".join(diff)


async def process_link(app, link):
    try:
        bot = app.bot
        link_id, user_id, url, old_content = link

        user_lang = "ar"
        if app.user_data and user_id in app.user_data:
            user_lang = app.user_data[user_id].get("lang", "ar")
        
        lang_dict = TEXTS.get(user_lang, TEXTS["ar"])

        new_content = await asyncio.to_thread(fetch_content, url)
        if not new_content:
            return

        if old_content and new_content != old_content:

            diff_text = get_diff(old_content, new_content, lang_dict)

            if len(diff_text) > 3500:
                diff_text = diff_text[:3500] + lang_dict["diff_truncated"]

            msg = lang_dict["site_changed"].format(url=url, diff_text=diff_text)

            await bot.send_message(
                chat_id=user_id,
                text=msg,
                parse_mode="Markdown"
            )

            update_content(link_id, new_content)

    except Exception as e:
        print(f"Error processing {link}: {e}")


async def start_monitor(app):
    while True:
        try:
            links = get_links()

            tasks = [
                process_link(app, link)
                for link in links
            ]

            if tasks:
                await asyncio.gather(*tasks)

        except Exception as e:
            print(f"Monitor loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)