# tikers.py
from telebot import types
from datetime import datetime
from tradingview_ta import TA_Handler, Interval, Exchange
import time, os
import db
import logging

logging.basicConfig(level=logging.INFO)

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
    ticker_name = message.text
    logging.info(f"Ticker name entered by user: {ticker_name}")
    bot.send_message(chat_id, "Введите точку входа:")
    bot.register_next_step_handler(message, lambda message: process_entry_point(bot, message, ticker_name))


def process_entry_point(bot, message, ticker_name):
    print("Ticker name received:", ticker_name)
    entry_point = float(message.text)
    bot.send_message(message.chat.id, "Введите тейк-профит:")
    bot.register_next_step_handler(message, lambda message: process_take_profit(bot, message, ticker_name, entry_point))

def process_take_profit(bot, message, ticker_name, entry_point):
    take_profit = float(message.text)
    bot.send_message(message.chat.id, "Введите стоп-лосс:")
    bot.register_next_step_handler(message, lambda message: process_stop_loss(bot, message, ticker_name, entry_point, take_profit))

def get_current_price(ticker_name):
    handler = TA_Handler(
        symbol=ticker_name,
        screener="crypto",  # Может быть изменено в зависимости от рынка: "crypto", "forex", "america"
        exchange="BINANCE",  # BYBIT, BINANCE
        interval=Interval.INTERVAL_1_MINUTE
    )
    try:
        analysis = handler.get_analysis()
        return analysis.indicators["close"]  # Получаем последнюю цену закрытия
    except Exception as e:
        print("Ошибка при получении данных с TradingView:", str(e))
        return None


def process_stop_loss(bot, message, ticker_name, entry_point, take_profit):
    stop_loss = float(message.text)
    current_rate = get_current_price(ticker_name)
    if current_rate is None:
        bot.send_message(message.chat.id, "Не удалось получить текущую стоимость тикера.")
        return

    # Уведомляем пользователя о текущей стоимости
    bot.send_message(message.chat.id, f"Текущая стоимость {ticker_name}: ${current_rate:.2f}")

    # Предложим выбрать направление сделки
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Long", callback_data=f"direction_Long_{ticker_name}_{entry_point}_{take_profit}_{stop_loss}_{current_rate}"))
    markup.add(types.InlineKeyboardButton("Short", callback_data=f"direction_Short_{ticker_name}_{entry_point}_{take_profit}_{stop_loss}_{current_rate}"))
    bot.send_message(message.chat.id, "Выберите направление:", reply_markup=markup)


# def process_stop_loss(bot, message, ticker_name, entry_point, take_profit):
#     stop_loss = float(message.text)
#     current_rate = get_current_price(ticker_name)
#     if current_rate is None:
#         bot.send_message(message.chat.id, "Не удалось получить текущую стоимость тикера.")
#         return
#     markup = types.InlineKeyboardMarkup()
#     markup.add(types.InlineKeyboardButton("Long", callback_data=f"direction_Long_{ticker_name}_{entry_point}_{take_profit}_{stop_loss}_{current_rate}"))
#     markup.add(types.InlineKeyboardButton("Short", callback_data=f"direction_Short_{ticker_name}_{entry_point}_{take_profit}_{stop_loss}_{current_rate}"))
#     bot.send_message(message.chat.id, "Выберите направление:", reply_markup=markup)

def process_current_rate(bot, message, ticker_name, entry_point, take_profit, stop_loss):
    current_rate = float(message.text)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Long", callback_data=f"direction_Long_{ticker_name}_{entry_point}_{take_profit}_{stop_loss}_{current_rate}"))
    markup.add(types.InlineKeyboardButton("Short", callback_data=f"direction_Short_{ticker_name}_{entry_point}_{take_profit}_{stop_loss}_{current_rate}"))
    bot.send_message(message.chat.id, "Выберите направление:", reply_markup=markup)

def process_direction(bot, call):
    data = call.data.split('_')
    direction = data[1]
    ticker_name = data[2]
    entry_point = float(data[3])
    take_profit = float(data[4])
    stop_loss = float(data[5])
    current_rate = float(data[6])
    
    bot.send_message(call.message.chat.id, "Прикрепите изображение сетапа:")
    bot.register_next_step_handler(call.message, lambda message: process_setup_image(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate, direction))

def process_setup_image(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate, direction):
    if message.content_type == 'photo':
        # Получаем информацию о файле
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)

        # Загружаем файл
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Создаем папку setups если она не существует
        directory = 'setups'
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Формируем путь к файлу
        # timestamp = int(time.time())
        timestamp = datetime.now().strftime("%d.%m.%Y-%H-%M-%S")
        file_path = f'{directory}/{ticker_name}_{timestamp}.jpg'
        
        # Сохраняем файл локально
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Путь к файлу, который будет сохранен в базе данных
        setup_image_path = file_path
    else:
        setup_image_path = None

    # Добавляем запись о новом тикере в базу данных
    db.add_new_ticker(ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction)
    bot.send_message(message.chat.id, "Тикер успешно добавлен!")


def process_setup_current(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate, direction):
    if message.content_markdown == 'поэтому':
        photo_id = message.photo[-1].file_id
        file_info = bot.get_file(photo_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Создаем папку, если она еще не существует
        if not os.path.exists('setups'):
            os.makedirs('setups')

        # Формируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{ticker_name}_{timestamp}.jpg"
        file_path = os.path.join('setups', filename)

        # Сохраняем файл
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Обновляем путь файла для сохранения в базе данных
        setup_image_path = file_path
    else:
        setup_image_path = None

    db.add_new_ticker(ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction)
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
