import asyncio
import difflib
from database import get_active_links, update_content, get_all_users_expiry, update_last_warning
from utils import fetch_content
from config import CHECK_INTERVAL
from lang import TEXTS
from datetime import datetime


def get_diff(old, new, lang_dict):
    diff = list(difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        n=0,
        lineterm=""
    ))
    
    additions = []
    deletions = []
    
    for line in diff:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue
        if line.startswith('+'):
            text = line[1:].strip()
            if text: additions.append(text)
        elif line.startswith('-'):
            text = line[1:].strip()
            if text: deletions.append(text)
            
    res = []
    if additions:
        res.append(f"🟢 **{lang_dict.get('additions', 'إضافات جديدة:')}**\n" + "\n".join(f"+ {a}" for a in additions))
    if deletions:
        res.append(f"🔴 **{lang_dict.get('deletions', 'نصوص محذوفة:')}**\n" + "\n".join(f"- {d}" for d in deletions))
        
    if not res:
        return "🔄 تغير في التنسيق الداخلي أو خصائص غير نصية."
        
    return "\n\n".join(res)


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


async def check_expiries(app):
    while True:
        try:
            bot = app.bot
            users = get_all_users_expiry()
            now = datetime.now()
            warning_milestones = [7, 5, 3, 2, 1, 0]

            for user_id, expiry_str, last_warning in users:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                delta = expiry_date - now
                days_left = delta.days

                user_lang = "ar"
                if app.user_data and user_id in app.user_data:
                    user_lang = app.user_data[user_id].get("lang", "ar")
                lang_dict = TEXTS.get(user_lang, TEXTS["ar"])

                # Find the next appropriate warning level
                applicable_warnings = [m for m in warning_milestones if days_left <= m]
                
                if applicable_warnings:
                    current_warning = max(applicable_warnings) # The largest milestone we've hit or passed
                    
                    if last_warning == -1 or current_warning < last_warning:
                        msg = lang_dict.get("expiry_warning", "⚠️ تنبيه: اشتراكك سينتهي قريباً.").format(days=current_warning)
                        if current_warning == 0:
                            msg = lang_dict.get("expired_message", "⚠️ اشتراكك الشهري انتهى.")
                        
                        try:
                            await bot.send_message(
                                chat_id=user_id,
                                text=msg,
                                parse_mode="Markdown"
                            )
                            update_last_warning(user_id, current_warning)
                        except Exception as e:
                            print(f"Failed to send expiry warning to {user_id}: {e}")

        except Exception as e:
            print(f"Expiry checker error: {e}")

        await asyncio.sleep(CHECK_INTERVAL * 6) # Check expiries less frequently, e.g., every 6 intervals


async def start_monitor(app):
    asyncio.create_task(check_expiries(app))
    while True:
        try:
            links = get_active_links()

            tasks = [
                process_link(app, link)
                for link in links
            ]

            if tasks:
                await asyncio.gather(*tasks)

        except Exception as e:
            print(f"Monitor loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)