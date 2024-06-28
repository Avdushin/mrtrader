import telebot
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    thread_id = message.message_thread_id if message.message_thread_id else "General"
    response_text = f"Тема: {thread_id}\nТекст: {message.text}"
    bot.reply_to(message, response_text)

bot.polling()
