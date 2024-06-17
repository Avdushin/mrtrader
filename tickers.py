# tikers.py
from telebot import types
from datetime import datetime
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
    print("Ticker name received:", ticker_name)  # Исправлено для отладки
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

# def process_setup_image(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate):
#     if message.content_type == 'photo':
#         setup_image_path = message.photo[-1].file_id
#     else:
#         setup_image_path = None
#     db.add_new_ticker(ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path)
#     bot.send_message(message.chat.id, "Тикер успешно добавлен!")

def process_setup_image(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate):
    if message.content_type == 'photo':
        # Получаем информацию о файле
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)

        # Загружаем файл
        downloaded_file = bot.download_file(file_info.file_path)  # Используем file_path из file_info
        
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
    db.add_new_ticker(ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path)
    bot.send_message(message.chat.id, "Тикер успешно добавлен!")


def process_setup_current(bot, message, ticker_name, entry_point, take_profit, stop_loss, current_rate):
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
