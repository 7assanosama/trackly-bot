import asyncio
from database import get_links, update_content
from utils import fetch_content
from config import CHECK_INTERVAL

async def start_monitor(bot):
    while True:
        links = get_links()

        for link in links:
            link_id, user_id, url, old_content = link

            new_content = fetch_content(url)
            if not new_content:
                continue

            if old_content and new_content != old_content:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"🚨 الموقع اتغير:\n{url}"
                )

                update_content(link_id, new_content)

        await asyncio.sleep(CHECK_INTERVAL)
