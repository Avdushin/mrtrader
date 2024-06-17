# config.py
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',')]

IMAGE_UPLOAD_PATH = 'setups'