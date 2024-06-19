# tickers.py
from telebot import types
from datetime import datetime, timedelta
from tradingview_ta import TA_Handler, Interval, Exchange
from admin import is_admin
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
import pytz
from utils import *
import config
import os
import db
import logging

# Настройка логгирования для APScheduler
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
global_bot = None

# Словарь для отслеживания времени последнего уведомления
alert_sent = {}
last_alert_time = {}

EXCHANGES = ['BINANCE', 'BYBIT', 'BINGX', 'KRAKEN', 'COINBASE']

def manage_tickers(bot, message):
    markup = types.InlineKeyboardMarkup()
    # Все пользователи видят кнопку "Список тикеров"
    markup.row(types.InlineKeyboardButton("Список тикеров", callback_data="show_tickers"))
    
    # Только администраторы видят остальные кнопки
    if is_admin(message.from_user.id):
        markup.row(types.InlineKeyboardButton("Добавить тикер", callback_data="add_ticker"))
        markup.row(types.InlineKeyboardButton("Редактировать тикер", callback_data="edit_ticker"))
        markup.row(types.InlineKeyboardButton("Удалить тикер", callback_data="delete_ticker"))
    
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


def initiate_add_ticker(bot, call):
    markup = types.InlineKeyboardMarkup()
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Введите имя тикера:")
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.register_next_step_handler(msg, ask_for_exchange, bot)

def ask_for_exchange(message, bot):
    ticker_name = message.text.strip().upper()
    markup = types.InlineKeyboardMarkup()
    for exchange in EXCHANGES:
        markup.add(types.InlineKeyboardButton(exchange, callback_data=f"exchange_{exchange}_{ticker_name}"))
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
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
    markup = types.InlineKeyboardMarkup()
    # Парсинг callback_data, чтобы извлечь нужные параметры
    _, direction, ticker_name, exchange, current_rate_str = call.data.split('_')
    try:
        current_rate = float(current_rate_str)
    except ValueError:
        bot.send_message(call.message.chat.id, "Ошибка при конвертации текущего курса в число.")
        return
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    # Передаем в следующий шаг все значения как есть, не пытаясь конвертировать направление сделки в число
    bot.send_message(call.message.chat.id, f"Введите точку входа для {ticker_name} ({direction}):", reply_markup=markup)
    bot.register_next_step_handler(call.message, process_entry_point, bot, ticker_name, exchange, direction, current_rate)


def process_entry_point(message, bot, ticker_name, exchange, direction, current_rate):
    markup = types.InlineKeyboardMarkup()
    try:
        entry_point = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для точки входа.")
        return  # Возврат в функцию для повторного ввода
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.send_message(message.chat.id, "Введите значение тейк-профит:")
    bot.register_next_step_handler(message, process_take_profit, bot, ticker_name, exchange, direction, entry_point, current_rate)

def process_take_profit(message, bot, ticker_name, exchange, direction, entry_point, current_rate):
    markup = types.InlineKeyboardMarkup()
    try:
        take_profit = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для тейк-профит.")
        return  # Возврат в функцию для повторного ввода
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.send_message(message.chat.id, "Введите значение стоп-лосс:")
    bot.register_next_step_handler(message, process_stop_loss, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate)

def process_stop_loss(message, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate):
    markup = types.InlineKeyboardMarkup()
    try:
        stop_loss = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для стоп-лосс.")
        return  # Возврат в функцию для повторного ввода
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
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

# def get_current_price(ticker_name, exchange):
#     handler = TA_Handler(symbol=ticker_name, screener="crypto", exchange=exchange, interval=Interval.INTERVAL_1_MINUTE)
#     try:
#         analysis = handler.get_analysis()
#         return analysis.indicators["close"]
#     except Exception as e:
#         logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {e}")
#         return None


# def get_current_price(ticker_name):
#     handler = TA_Handler(symbol=ticker_name, screener="crypto", interval=Interval.INTERVAL_1_MINUTE)
#     for exchange in EXCHANGES:
#         handler.exchange = exchange
#         try:
#             analysis = handler.get_analysis()
#             return exchange, analysis.indicators["close"]
#         except Exception as e:
#             logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {e}")
#     return None, None


# def get_current_price(ticker_name, exchange):
#     handler = TA_Handler(symbol=ticker_name, screener="crypto", exchange=exchange, interval=Interval.INTERVAL_1_MINUTE)
#     try:
#         analysis = handler.get_analysis()
#         return analysis.indicators["close"]
#     except Exception as e:
#         logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {e}")
#         return None
# def get_current_price(ticker_name, exchange):
#     handler = TA_Handler(symbol=ticker_name, screener="crypto", exchange=exchange, interval=Interval.INTERVAL_1_MINUTE)
#     try:
#         analysis = handler.get_analysis()
#         return analysis.indicators["close"]
#     except Exception as e:
#         logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {e}")
#         return None


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
                f"<b>Текущая стоимость:</b> <code>${get_current_price(ticker[1], 'BYBIT')}</code>\n"
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
# def start_monitoring(bot):
#     global global_bot
#     global_bot = bot
#     scheduler = BackgroundScheduler(timezone=utc)
#     scheduler.add_job(monitor_prices, 'interval', seconds=3)
#     scheduler.start()

# def start_monitoring(bot):
#     global global_bot
#     global_bot = bot
#     scheduler = BackgroundScheduler(timezone=utc)
#     scheduler.add_job(monitor_prices, 'interval', seconds=3)
#     scheduler.start()
#     logging.info(f"Admin Chat IDs loaded: {config.ADMIN_CHAT_IDS}")


def start_monitoring(bot):
    global global_bot
    global_bot = bot
    moscow_tz = pytz.timezone('Europe/Moscow')
    scheduler = BackgroundScheduler(timezone=moscow_tz)
    scheduler.add_job(monitor_prices, 'interval', seconds=3)
    scheduler.start()
    logging.info(f"Admin Chat IDs loaded: {config.ADMIN_CHAT_IDS}")

def send_alert(ticker_id, message_text):
    now = datetime.now()
    if ticker_id in last_alert_time:
        # Проверяем, прошло ли 5 минут
        if now - last_alert_time[ticker_id] < timedelta(minutes=5):
            print(f"Alert for {ticker_id} suppressed to avoid spam.")
            return  # Не отправляем уведомление, если не прошло 5 минут
    # Обновляем время последнего уведомления и отправляем сообщение
    last_alert_time[ticker_id] = now
    for chat_id in config.ADMIN_CHAT_IDS:
        try:
            global_bot.send_message(chat_id=chat_id, text=message_text)
            logging.info(f"Sent alert to {chat_id}: {message_text}")
        except Exception as e:
            logging.error(f"Failed to send alert to {chat_id}: {str(e)}")

# def send_alert(message_text):
#     print("Admin Chat IDs:", config.ADMIN_CHAT_IDS)
#     for chat_id in config.ADMIN_CHAT_IDS:
#         try:
#             global_bot.send_message(chat_id=chat_id, text=message_text)
#             logging.info(f"Sent alert to {chat_id}: {message_text}")
#         except Exception as e:
#             logging.error(f"Failed to send alert to {chat_id}: {str(e)}")


# def send_alert(message_text):
#     for chat_id in config.ADMIN_CHAT_IDS:
#         try:
#             global_bot.send_message(chat_id=chat_id, text=message_text)
#             logging.info(f"Sent alert to {chat_id}: {message_text}")
#         except Exception as e:
#             logging.error(f"Failed to send alert to {chat_id}: {str(e)}")

def monitor_prices():
    logging.info("Начало мониторинга цен...")
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, ticker, entry_point, take_profit, stop_loss FROM tickers WHERE active=1")
        tickers = cursor.fetchall()
        if not tickers:
            logging.info("Активные тикеры для мониторинга не найдены.")
        for ticker in tickers:
            ticker_id, ticker_name, entry_point, take_profit, stop_loss = ticker
            logging.info(f"Мониторинг тикера: {ticker_name} на BYBIT")
            current_rate = get_current_price(ticker_name, "BYBIT")
            if current_rate:
                logging.info(f"Текущий курс для {ticker_name} на BYBIT составляет {current_rate}")
                message_text = check_price_thresholds(ticker_name, "BYBIT", entry_point, take_profit, stop_loss, current_rate, ticker_id)
                if message_text:
                    send_alert(ticker_id, message_text)
            else:
                logging.error(f"Не удалось получить текущий курс для {ticker_name} на BYBIT.")
    except Exception as e:
        logging.error(f"Ошибка во время мониторинга цен: {e}")
    finally:
        cursor.close()
        connection.close()


def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
    message_text = ""
    if abs(current_rate - entry_point) / entry_point < 0.015:
        message_text += f"🚨 {ticker_name} находится в пределах 1.5% от точки входа на {exchange}: {entry_point} (текущая цена: {current_rate})\n"
    if current_rate == entry_point:
        message_text += f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
    if current_rate >= take_profit:
        message_text += f"🎉 {ticker_name} достиг уровеня тейк-профита: ${take_profit}.\n"
        db.update_ticker_active(ticker_id, False)
    if current_rate <= stop_loss:
        message_text += f"🛑 {ticker_name} достиг уровня стоп-лосса на {stop_loss}.\n"
        db.update_ticker_active(ticker_id, False)
    return message_text

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     message_text = ""
#     if abs(current_rate - entry_point) / entry_point < 0.015:
#         message_text += f"🚨 {ticker_name} is within 1.5% of the entry point on {exchange}: {entry_point} (current price: {current_rate})\n"
#     if current_rate == entry_point:
#         message_text += f"✅ {ticker_name} has reached the entry point on {exchange}.\n"
#     if current_rate >= take_profit:
#         message_text += f"🎉 {ticker_name} has reached take profit on {exchange}.\n"
#         db.update_ticker_active(ticker_id, False)
#     if current_rate <= stop_loss:
#         message_text += f"🛑 {ticker_name} has hit stop loss on {exchange}.\n"
#         db.update_ticker_active(ticker_id, False)
#     return message_text

