# tikers.py
from telebot import types
from datetime import datetime
from tradingview_ta import TA_Handler, Interval, Exchange
import os
import logging

logging.basicConfig(level=logging.INFO)

def manage_tickers(bot, message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Добавить тикер", callback_data="add_ticker"))
    markup.row(types.InlineKeyboardButton("Редактировать тикер", callback_data="edit_ticker"))
    markup.row(types.InlineKeyboardButton("Удалить тикер", callback_data="delete_ticker"))
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

def initiate_add_ticker(bot, call):
    bot.answer_callback_query(call.id)
    markup = create_cancel_markup()
    msg = bot.send_message(call.message.chat.id, "Введите имя тикера (название монеты):", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda message: process_ticker_name(bot, message))

def process_ticker_name(bot, message):
    ticker_name = message.text.strip().upper()
    ask_for_exchange(bot, message, ticker_name)

def ask_for_exchange(bot, message, ticker_name):
    markup = types.InlineKeyboardMarkup()
    exchanges = ["BINANCE", "BYBIT", "BINGX"]
    for exchange in exchanges:
        markup.add(types.InlineKeyboardButton(exchange, callback_data=f"exchange_{exchange}_{ticker_name}"))
    markup.row(types.InlineKeyboardButton("Отмена", callback_data="cancel"))
    bot.send_message(message.chat.id, "Выберите биржу:", reply_markup=markup)

def handle_exchange_selection(bot, call):
    _, exchange, ticker_name = call.data.split('_')
    current_rate = get_current_price(ticker_name, exchange)
    if current_rate is None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Выбрать другую биржу", callback_data=f"change_exchange_{ticker_name}"))
        markup.add(types.InlineKeyboardButton("Ввести новое название тикера", callback_data="new_ticker"))
        markup.row(types.InlineKeyboardButton("Отмена", callback_data="cancel"))
        bot.send_message(call.message.chat.id, "Попробуйте другую биржу или измените тикер:", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("Пропустить", callback_data=f"skip_setup_{ticker_name}_{exchange}_{current_rate}"))
        markup.row(types.InlineKeyboardButton("Отмена", callback_data="cancel"))
        bot.send_message(call.message.chat.id, f"Текущая стоимость {ticker_name} на {exchange}: ${current_rate:.2f}", reply_markup=markup)
        bot.send_message(call.message.chat.id, "Прикрепите изображение сетапа или отправьте любой текст, чтобы пропустить.", reply_markup=markup)

def create_skip_cancel_markup():
    """ Helper function to create a skip and cancel buttons """
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Пропустить", callback_data="skip"))
    markup.add(types.InlineStreamKeyboardButton("Отмена", callback_data="cancel"))
    return markup

def get_current_price(ticker_name, exchange):
    handler = TA_Handler(
        symbol=ticker_name,
        screener="crypto",
        exchange=exchange,
        interval=Interval.INTERVAL_1_MINUTE
    )
    try:
        analysis = handler.get_analysis()
        return analysis.indicators["close"]
    except Exception as e:
        logging.error(f"Ошибка при получении данных: {e}")
        return None

def create_cancel_markup():
    """ Helper function to create a cancel button """
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Отмена", callback_data="cancel"))
    return markup

def process_setup_image(bot, message, ticker_name, exchange, current_rate):
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        directory = 'setups'
        if not os.path.exists(directory):
            os.makedirs(directory)
        timestamp = datetime.now().strftime("%d.%m.%Y-%H-%M-%S")
        file_path = f'{directory}/{ticker_name}_{timestamp}.jpg'
        with open(file_path, 'wb') as new_file:
            new_map.write(downloaded_file)
        setup_image_path = file_path
    else:
        setup_image_path = "Пропущено пользователем"
    
    bot.send_message(message.chat.id, "Введите точку входa:", reply_markup=create_cancel_markup())
    bot.register_next_step_handler(message, lambda msg: process_entry_point(bot, msg, ticker_name, exchange, current_rate, setup_image_path))

# def process_setup_image(bot, message, ticker_name, exchange, current_rate):
#     if message.content_type == 'photo':
#         file_id = message.photo[-1].file_id
#         file_info = bot.get_file(file_id)
#         downloaded_file = bot.download_file(file_info.file_path)
#         directory = 'setups'
#         if not os.path.exists(directory):
#             os.makedirs(directory)
#         timestamp = datetime.now().strftime("%d.%m.%Y-%H-%M-%S")
#         file_path = f'{directory}/{ticker_name}_{timestamp}.jpg'
#         with open(file_path, 'wb') as new_file:
#             new_file.write(downloaded_file)
#         setup_image_path = file_path
#     else:
#         setup_image_path = "Пропущено пользователем"
#     markup = create_cancel_markup()
#     bot.send_message(message.chat.id, "Введите точку входа:", reply_markup=markup)
#     bot.register_next_step_handler(message, lambda msg: process_entry_point(bot, msg, ticker_name, exchange, current_rate, setup_image_path))

def process_entry_point(message, ticker_name, exchange, current_rate):
    try:
        entry_point = float(message.text)
        markup = create_cancel_markup()
        bot.send_message(message.chat.id, "Введите тейк-профит:", reply_markup=markup)
        # Здесь можно сохранить entry_point в состоянии
        user_state[message.chat.id]['entry_point'] = entry_point
        bot.register_next_step_handler(message, lambda msg: process_take_profit(msg, ticker_name, exchange, entry_point, current_rate))
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите числовое значение для точки входа.")


# def process_entry_point(bot, message, ticker_name, exchange, current_rate, setup_image_path):
#     try:
#         entry_point = float(message.text)
#         markup = create_cancel_markup()
#         bot.send_message(message.chat.id, "Введите тейк-профит:", reply_markup=markup)
#         bot.register_next_step_handler(message, lambda msg: process_take_profit(bot, msg, ticker_name, exchange, entry_point, current_rate, setup_image_path))
#     except ValueError:
#         bot.send_message(message.chat.id, "Пожалуйста, введите числовое значение для точки входа.")

def process_take_profit(bot, message, ticker_name, exchange, entry_point, current_rate, setup_image_path):
    try:
        take_profit = float(message.text)
        markup = create_cancel_markup()
        bot.send_message(message.chat.id, "Введите стоп-лосс:", reply_markup=markup)
        bot.register_next_step_handler(message, lambda msg: process_stop_loss(bot, msg, ticker_name, exchange, entry_point, take_profit, current_rate, setup_image_path))
    except ValueError:
        bot.send_message(message.chat_id, "Пожалуйста, введите числовое значение для тейк-профит.")

def process_stop_loss(bot, message, ticker_name, exchange, entry_point, take_profit, current_rate, setup_image_path):
    try:
        stop_loss = float(message.text)
        bot.send_message(message.chat_id, f"Тикер {ticker_name} добавлен. Сетап: {setup_image_back_path}, Точка входа: {entry_point}, Тейк-профит: {take_profit}, Стоп-лосс: {stop_loss}.")
        # Здесь может быть код для сохранения данных тикера в базу данных
    except ValueError:
        bot.send_message(message.chat_id, "Пожалуйста, введите числовое значение для стоп-лосс.")

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