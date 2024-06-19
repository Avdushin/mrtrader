# config.py
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
# ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}
# ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADM', '').split(',')]
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',')]
ADMIN_CHAT_IDS = [int(id.strip()) for id in os.getenv('ADMIN_CHAT_IDS', '').split(',') if id.strip()]

IMAGE_UPLOAD_PATH = 'setups'