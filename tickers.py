# tickers.py
from telebot import types
from datetime import datetime
from tradingview_ta import TA_Handler, Interval, Exchange
import os
import db
import logging

logging.basicConfig(level=logging.INFO)

EXCHANGES = ['BINANCE', 'BYBIT', 'KRAKEN', 'COINBASE']

def manage_tickers(bot, message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Добавить тикер", callback_data="add_ticker"))
    markup.row(types.InlineKeyboardButton("Редактировать тикер", callback_data="edit_ticker"))
    markup.row(types.InlineKeyboardButton("Удалить тикер", callback_data="delete_ticker"))
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

def initiate_add_ticker(bot, call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Введите имя тикера:")
    bot.register_next_step_handler(msg, ask_for_exchange, bot)

def ask_for_exchange(message, bot):
    ticker_name = message.text.strip().upper()
    markup = types.InlineKeyboardMarkup()
    for exchange in EXCHANGES:
        markup.add(types.InlineKeyboardButton(exchange, callback_data=f"exchange_{exchange}_{ticker_name}"))
    bot.send_message(message.chat.id, "Выберите биржу:", reply_markup=markup)

def handle_exchange_selection(bot, call):
    _, exchange, ticker_name = call.data.split('_')
    bot.answer_callback_query(call.id)
    current_rate = get_current_price(ticker_name, exchange)
    if current_rate is None:
        bot.send_message(call.message.chat.id, "Не удалось получить текущую цену тикера, попробуйте другую биржу.")
        return
    bot.send_message(call.message.chat.id, f"Текущая цена {ticker_name} на {exchange}: {current_rate}")
    ask_for_direction(bot, call.message, ticker_name, exchange, current_rate)

def ask_for_direction(bot, message, ticker_name, exchange, current_rate):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Long", callback_data=f"direction_long_{ticker_name}_{exchange}_{current_rate}"),
               types.InlineKeyboardButton("Short", callback_data=f"direction_short_{ticker_name}_{exchange}_{current_rate}"))
    bot.send_message(message.chat.id, "Выберите направление сделки:", reply_markup=markup)

def process_direction(bot, call):
    # Парсинг callback_data, чтобы извлечь нужные параметры
    _, direction, ticker_name, exchange, current_rate_str = call.data.split('_')
    try:
        current_rate = float(current_rate_str)
    except ValueError:
        bot.send_message(call.message.chat.id, "Ошибка при конвертации текущего курса в число.")
        return

    # Передаем в следующий шаг все значения как есть, не пытаясь конвертировать направление сделки в число
    bot.send_message(call.message.chat.id, f"Введите точку входа для {ticker_name} ({direction}):")
    bot.register_next_step_handler(call.message, process_entry_point, bot, ticker_name, exchange, direction, current_rate)


def process_entry_point(message, bot, ticker_name, exchange, direction, current_rate):
    try:
        entry_point = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для точки входа.")
        return  # Возврат в функцию для повторного ввода
    bot.send_message(message.chat.id, "Введите значение тейк-профит:")
    bot.register_next_step_handler(message, process_take_profit, bot, ticker_name, exchange, direction, entry_point, current_rate)

def process_take_profit(message, bot, ticker_name, exchange, direction, entry_point, current_rate):
    try:
        take_profit = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для тейк-профит.")
        return  # Возврат в функцию для повторного ввода
    bot.send_message(message.chat.id, "Введите значение стоп-лосс:")
    bot.register_next_step_handler(message, process_stop_loss, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate)

def process_stop_loss(message, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate):
    try:
        stop_loss = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для стоп-лосс.")
        return  # Возврат в функцию для повторного ввода
    bot.send_message(message.chat.id, "Прикрепите изображение сетапа или отправьте URL:")
    bot.register_next_step_handler(message, finalize_setup, bot, ticker_name, exchange, direction, entry_point, take_profit, stop_loss, current_rate)


def finalize_setup(message, bot, ticker_name, exchange, direction, entry_point, take_profit, stop_loss, current_rate):
    setup_image_path = message.text if message.content_type == 'text' else save_photo(bot, message.photo[-1].file_id)
    try:
        db.add_new_ticker(ticker_name, direction, entry_point, take_profit, stop_loss, current_rate, setup_image_path)
        bot.send_message(message.chat.id, "Тикер успешно добавлен в ваш портфель!")
        print(f"Данные тикера для добавления в БД:  \n Название тикера: {ticker_name} \n Направление сделки: {direction} \n Точка входа: {entry_point} \n Тейк-профит: {take_profit} \n Стоп-лосс: {stop_loss} \n Текущий курс {current_rate} \n  Сетап: {setup_image_path}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при добавлении данных: {e}")

def save_photo(bot, file_id):
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    directory = 'setups'
    if not os.path.exists(directory):
        os.makedirs(directory)
    timestamp = datetime.now().strftime("%d.%m.%Y-%H-%M-%S")
    file_path = f'{directory}/{timestamp}.jpg'
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)
    return file_path

def get_current_price(ticker_name, exchange):
    handler = TA_Handler(symbol=ticker_name, screener="crypto", exchange=exchange, interval=Interval.INTERVAL_1_MINUTE)
    try:
        analysis = handler.get_analysis()
        return analysis.indicators["close"]
    except Exception as e:
        logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {e}")
        return None

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
