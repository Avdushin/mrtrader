# bot.py
import telebot
from config import TOKEN
from tickers import monitor_tickers
import commands
import db

bot = telebot.TeleBot(TOKEN)

if __name__ == "__main__":
    db.setup_database()
    commands.register_handlers(bot)
    bot.polling(none_stop=True)
    monitor_tickers(bot)
