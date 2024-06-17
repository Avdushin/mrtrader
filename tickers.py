# tikers.py
from telebot import types
import db

def manage_tickers(bot, message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Добавить тикер", callback_data="add_ticker"))
    markup.row(types.InlineKeyboardButton("Редактировать тикер", callback_data="edit_ticker"))
    markup.row(types.InlineKeyboardButton("Удалить тикер", callback_data="delete_ticker"))
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

def handle_action(bot, call):
    # Define your action handling logic here
    pass

def initiate_add_ticker(bot, call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Введите имя тикера:")
    bot.register_next_step_handler(msg, lambda message: process_ticker_name(bot, message))

def process_ticker_name(bot, message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Введите точку входа:")
    bot.register_next_step_handler(message, lambda message: process_entry_point(bot, message, message.text))

def process_entry_point(bot, message, ticker_name):
    entry_point = float(message.text)
    bot.send_message(message.chat.id, "Введите тейк-профит:")
    bot.register_next_step_handler(message, lambda message: process_take_profit(bot, message, ticker_name, entry_point))

def process_take_profit(bot, message, ticker_name, entry_point):
    take_profit = float(message.text)
    bot.send_message(message.chat.id, "Введите стоп-лосс:")
    bot.register_next_step_handler(message, lambda message: process_stop_loss(bot, message, ticker_name, entry_point, take_profit))

def process_stop_loss(bot, message, ticker_name, entry_point, take_profit):
    stop_loss = float(message.text)
    bot.send_message(message.chat.id, "Введите текущую стоимость:")
    bot.register_next_step_handler(message, lambda message: process_current_rate(bot, message, ticker_name, entry_point, take_profit, stop_loss))

def process_current_rate(bot, message, ticker_name, entry_point, take_profit, stop_loss):
    current_rate = float(message.text)
    bot.send_message(message.chat.id, "Прикрепите изображение сетапа:")
    bot.register_next_step_handler(message, lambda message: process_setup_image(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate))

def process_setup_image(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate):
    if message.content_type == 'photo':
        setup_image_path = message.photo[-1].file_id
    else:
        setup_image_path = None
    db.add_new_ticker(ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path)
    bot.send_message(message.chat.id, "Тикер успешно добавлен!")

def delete_ticker(bot, call):
    chat_id = call.message.chat.id
    tickers = db.get_all_tickers()
    markup = types.InlineKeyboardMarkup()
    for ticker in tickers:
        markup.add(types.InlineKeyboardButton(ticker['name'], callback_data=f"del_{ticker['id']}"))
    bot.send_message(chat_id, "Выберите тикер для удаления:", reply_markup=markup)

def confirm_delete_ticker(bot, call):
    ticker_id = int(call.data.split("_")[2])
    db.delete_ticker(ticker_id)
    bot.answer_callback_query(call.id, "Тикер удален!")
