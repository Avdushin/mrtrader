# bot.py
import telebot
import threading
from config import TOKEN
from tickers import start_monitoring
import commands
import db

bot = telebot.TeleBot(TOKEN)

def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    db.setup_database()
    commands.register_handlers(bot)
    threading.Thread(target=start_monitoring, args=(bot,)).start()
    run_bot()
