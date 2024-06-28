import telebot
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    chat_id = message.chat.id
    try:
        msg_thread_id = message.reply_to_message.message_thread_id
    except AttributeError:
        msg_thread_id = "General"
    bot.reply_to(message, f"Chat ID этого чата: {chat_id}\nИ message_thread_id: {msg_thread_id}")

bot.polling()