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
GODS = [int(id.strip()) for id in os.getenv('GODS', '').split(',')]
ADMIN_CHAT_IDS = [int(id.strip()) for id in os.getenv('ADMIN_CHAT_IDS', '').split(',') if id.strip()]
PREFERRED_CHAT_ID = [int(id.strip()) for id in os.getenv('PREFERRED_CHAT_ID', '').split(',') if id.strip()]
ALARM_CHAT_ID = int(os.getenv('ALARM_CHAT_ID'))
ALARM_THEME_ID = int(os.getenv('ALARM_THEME_ID')
)
print("БУТЕРБРОДНИЦА:", os.getenv('PREFERRED_CHAT_ID'))
print("GODS from env:", os.getenv('GODS'))
print("Admin Chat IDs from env:", os.getenv('ADMIN_CHAT_IDS'))

IMAGE_UPLOAD_PATH = 'setups'

GENERAL_EXCHANGES = {
    'BYBIT': 'BYBIT',
    'BINANCE': 'BINANCE',
    'BINGX': 'BINGX',
    'KRAKEN': 'KRAKEN',
    'COINBASE': 'COINBASE'
}