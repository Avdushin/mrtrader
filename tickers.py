# tickers.py
from telebot import types
from datetime import datetime
from tradingview_ta import TA_Handler, Interval, Exchange
import config
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from utils import *
import os
import db
import logging

# Настройка логгирования для APScheduler
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

EXCHANGES = ['BINANCE', 'BYBIT', 'KRAKEN', 'COINBASE']

def manage_tickers(bot, message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Список тикеров", callback_data="show_tickers"))
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

# Список тикеров
def show_ticker_list(bot, message):
    tickers = db.get_all_tickers()
    markup = types.InlineKeyboardMarkup()
    for ticker, id in tickers:
        markup.add(types.InlineKeyboardButton(ticker, callback_data=f"ticker_{id}"))
    bot.send_message(message.chat.id, "Выберите тикер:", reply_markup=markup)

# Информация о тикере
def show_ticker_info(bot, call):
    ticker_id = call.data.split('_')[1]
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM tickers WHERE id = %s", (ticker_id,))
        ticker = cursor.fetchone()
        if ticker:

            info = (
                f"<b>Тикер:</b> <code>{ticker[1]}</code>\n"
                f"<b>Точка входа (ТВХ):</b> <code>{ticker[2]}</code>\n"
                f"<b>Тейк-профит:</b> <code>{ticker[3]}</code>\n"
                f"<b>Стоп-лос:</b> <code>{ticker[4]}</code>\n"
                f"<b>Текущая стоимость:</b> <code>${get_current_price(ticker[1], 'BINANCE')}</code>\n"
                f"<b>Сетап:</b> <code>{ticker[6]}</code>\n"
                f"<b>Позиция:</b> <code>{ticker[8]}</code>"
            )
            bot.send_message(call.message.chat.id, info, parse_mode="HTML")
            if ticker[6] and os.path.exists(ticker[6]):
                bot.send_photo(call.message.chat.id, open(ticker[6], 'rb'))

            # В функции show_ticker_info
            df = fetch_financial_data(ticker[1], "BINANCE")  # Убедитесь, что ticker[1] содержит символ тикера
            chart_path = create_financial_chart(ticker[1], df)
            with open(chart_path, 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo)
            os.remove(chart_path)  # Очистка после отправки

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Failed to create chart: {str(e)}")
    finally:
        cursor.close()
        connection.close()

# Удаление тикеров
def delete_ticker(bot, call):
    tickers = db.get_all_tickers()
    markup = types.InlineKeyboardMarkup()
    for ticker in tickers:
        markup.add(types.InlineKeyboardButton(ticker[0], callback_data=f"del_{ticker[1]}"))  # Название тикера и его ID
    bot.send_message(call.message.chat.id, "Выберите тикер для удаления:", reply_markup=markup)

def confirm_delete_ticker(bot, call):
    parts = call.data.split("_")
    if len(parts) < 2:
        bot.send_message(call.message.chat.id, "Произошла ошибка при обработке вашего запроса.")
        return
    ticker_id = int(parts[1])
    db.delete_ticker(ticker_id)
    bot.answer_callback_query(call.id, "Тикер удален!")
    bot.edit_message_text("Тикер успешно удален.", call.message.chat.id, call.message.message_id)


# Редактировать тикер
# Функция для отображения списка тикеров при запросе на редактирование
def edit_ticker(bot, call):
    tickers = db.get_all_tickers()
    markup = types.InlineKeyboardMarkup()
    for ticker in tickers:
        markup.add(types.InlineKeyboardButton(ticker[0], callback_data=f"edit_{ticker[1]}"))  # Название тикера и его ID
    bot.send_message(call.message.chat.id, "Выберите тикер для редактирования:", reply_markup=markup)

# Функция для выбора поля, которое пользователь хочет отредактировать
def select_field_to_edit(bot, call):
    ticker_id = call.data.split("_")[1]
    markup = types.InlineKeyboardMarkup()
    fields = ["entry_point", "take_profit", "stop_loss", "current_rate", "active", "direction"]
    for field in fields:
        markup.add(types.InlineKeyboardButton(field.replace("_", " ").title(), callback_data=f"editfield_{ticker_id}_{field}"))
    bot.send_message(call.message.chat.id, "Выберите поле для редактирования:", reply_markup=markup)

# Функция для получения нового значения от пользователя
def get_new_value(bot, call):
    parts = call.data.split('_', 2)
    if len(parts) < 3:
        bot.send_message(call.message.chat.id, "Произошла ошибка при обработке вашего запроса.")
        return
    _, ticker_id, field = parts
    msg = f"Введите новое значение для {field.replace('_', ' ').title()}:"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_edit"))
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, lambda message: update_ticker_value(bot, message, ticker_id, field))

# Функция для обновления значения в базе данных
def update_ticker_value(bot, message, ticker_id, field):
    new_value = message.text
    try:
        db.update_ticker_field(ticker_id, field, new_value)
        bot.send_message(message.chat.id, f"Значение для {field.replace('_', ' ').title()} успешно обновлено!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при обновлении данных: {e}")

# Monitoring =================================================================
def monitor_prices():
    logging.info("Starting price monitoring...")
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, ticker, entry_point FROM tickers")
        # cursor.execute("SELECT id, ticker, entry_point FROM tickers WHERE active=TRUE")
        tickers = cursor.fetchall()
        for ticker in tickers:
            ticker_id, ticker_name, entry_point = ticker
            current_rate = get_current_price(ticker_name, 'BINANCE')
            if current_rate is not None:
                percent_difference = abs(current_rate - entry_point) / entry_point
                logging.info(f"Checked {ticker_name}: current rate {current_rate}, entry point {entry_point}")
                # if percent_difference <= 0.01:
                if percent_difference <= 0.05:
                    message_text = f"🚨 {ticker_name} приближается к точке входа: {entry_point} (текущая цена: {current_rate})"
                    bot.send_message(chat_id=config.ADMIN_CHAT_ID, text=message_text)
                    logging.info(f"Sent alert for {ticker_name}: {message_text}")
    except Exception as e:
        logging.error(f"Error during price monitoring: {str(e)}")
    finally:
        cursor.close()
        connection.close()

def start_monitoring():
    scheduler = BackgroundScheduler(timezone=utc)
    scheduler.add_job(monitor_prices, 'interval', seconds=1)
    scheduler.start()