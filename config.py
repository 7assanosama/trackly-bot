import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))