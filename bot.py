# bot.py
import telebot
from config import TOKEN
import commands
import db  # Импортируйте модуль db

bot = telebot.TeleBot(TOKEN)

if __name__ == "__main__":
    db.setup_database()
    commands.register_handlers(bot)
    bot.polling(none_stop=True)
