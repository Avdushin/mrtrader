# tickers.py
from telebot import types
from datetime import datetime, timedelta
from tradingview_ta import TA_Handler, Interval, Exchange
from apscheduler.schedulers.background import BackgroundScheduler
from config import PREFERRED_CHAT_ID, ALARM_CHAT_ID, ALARM_THEME_ID
import pytz
import config
import os
import db
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
global_bot = None

last_alert_time = {}

EXCHANGES = ['BYBIT', 'BINGX', 'BINANCE', 'KRAKEN', 'COINBASE']

def manage_tickers(bot, message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Список тикеров", callback_data="show_tickers"))
    markup.row(types.InlineKeyboardButton("Активные сделки", callback_data="active_trades"))
    markup.row(types.InlineKeyboardButton("Добавить тикер", callback_data="add_ticker"),
               types.InlineKeyboardButton("Редактировать тикер", callback_data="edit_ticker"),
               types.InlineKeyboardButton("Удалить тикер", callback_data="delete_ticker"))
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)


def initiate_add_ticker(bot, call):
    print("initiate_add_ticker called")
    markup = types.InlineKeyboardMarkup()
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Введите имя тикера:", message_thread_id=config.ALARM_THEME_ID)
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.register_next_step_handler(msg, ask_for_exchange, bot)

def ask_for_exchange(message, bot):
    ticker_name = message.text.strip().upper()
    markup = types.InlineKeyboardMarkup()
    for exchange in EXCHANGES:
        markup.add(types.InlineKeyboardButton(exchange, callback_data=f"exchange_{exchange}_{ticker_name}"))
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.send_message(message.chat.id, "Выберите биржу:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

def handle_exchange_selection(bot, call):
    parts = call.data.split('_', 2)
    if len(parts) < 3:
        bot.send_message(call.message.chat.id, "Ошибка в данных. Пожалуйста, попробуйте снова.", message_thread_id=config.ALARM_THEME_ID)
        return
    _, exchange, ticker_name = parts

    bot.answer_callback_query(call.id)
    exchange, current_rate = get_current_price(ticker_name)
    if current_rate is None:
        bot.send_message(call.message.chat.id, "Не удалось получить текущую цену тикера, попробуйте другую биржу.", message_thread_id=config.ALARM_THEME_ID)
        return
    bot.send_message(call.message.chat.id, f"Текущая цена {ticker_name} на {exchange}: {current_rate}", message_thread_id=config.ALARM_THEME_ID)
    ask_for_direction(bot, call.message, ticker_name, exchange, current_rate)

def ask_for_direction(bot, message, ticker_name, exchange, current_rate):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Long", callback_data=f"direction_long_{ticker_name}_{exchange}_{current_rate}"),
               types.InlineKeyboardButton("Short", callback_data=f"direction_short_{ticker_name}_{exchange}_{current_rate}"))
    bot.send_message(message.chat.id, "Выберите направление сделки:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

def process_direction(bot, call):
    markup = types.InlineKeyboardMarkup()
    _, direction, ticker_name, exchange, current_rate_str = call.data.split('_')
    try:
        current_rate = float(current_rate_str)
    except ValueError:
        bot.send_message(call.message.chat.id, "Ошибка при конвертации текущего курса в число.", message_thread_id=config.ALARM_THEME_ID)
        return
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.send_message(call.message.chat.id, f"Введите точку входа для {ticker_name} ({direction}):", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
    bot.register_next_step_handler(call.message, process_entry_point, bot, ticker_name, exchange, direction, current_rate)

def process_entry_point(message, bot, ticker_name, exchange, direction, current_rate):
    markup = types.InlineKeyboardMarkup()
    try:
        entry_point = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для точки входа.", message_thread_id=config.ALARM_THEME_ID)
        return
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.send_message(message.chat.id, "Введите значение тейк-профит:", message_thread_id=config.ALARM_THEME_ID)
    bot.register_next_step_handler(message, process_take_profit, bot, ticker_name, exchange, direction, entry_point, current_rate)

def process_take_profit(message, bot, ticker_name, exchange, direction, entry_point, current_rate):
    markup = types.InlineKeyboardMarkup()
    try:
        take_profit = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для тейк-профит.", message_thread_id=config.ALARM_THEME_ID)
        return
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.send_message(message.chat.id, "Введите значение стоп-лосс:", message_thread_id=config.ALARM_THEME_ID)
    bot.register_next_step_handler(message, process_stop_loss, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate)

def process_stop_loss(message, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate):
    markup = types.InlineKeyboardMarkup()
    try:
        stop_loss = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число для стоп-лосс.", message_thread_id=config.ALARM_THEME_ID)
        return
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    bot.send_message(message.chat.id, "Прикрепите изображение сетапа или отправьте URL:", message_thread_id=config.ALARM_THEME_ID)
    bot.register_next_step_handler(message, finalize_setup, bot, ticker_name, exchange, direction, entry_point, take_profit, stop_loss, current_rate)

def finalize_setup(message, bot, ticker_name, exchange, direction, entry_point, take_profit, stop_loss, current_rate):
    setup_image_path = message.text if message.content_type == 'text' else save_photo(bot, message.photo[-1].file_id)
    try:
        db.add_new_ticker(ticker_name, direction, entry_point, take_profit, stop_loss, current_rate, setup_image_path)
        bot.send_message(message.chat.id, "Тикер успешно добавлен в ваш портфель!", message_thread_id=config.ALARM_THEME_ID)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при добавлении данных: {e}", message_thread_id=config.ALARM_THEME_ID)

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

def get_current_price(ticker_name):
    handler = TA_Handler(interval=Interval.INTERVAL_1_MINUTE, screener="crypto")
    for exchange in EXCHANGES:
        handler.exchange = exchange
        handler.symbol = ticker_name
        try:
            analysis = handler.get_analysis()
            if analysis:
                current_rate = analysis.indicators.get("close")
                if current_rate is not None:
                    return exchange, current_rate
        except Exception as e:
            logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {str(e)}")
            continue
    logging.error(f"Failed to fetch data for {ticker_name} on all exchanges.")
    return None, None

def show_ticker_list(bot, message):
    tickers = db.get_all_tickers()
    markup = types.InlineKeyboardMarkup()
    for ticker, id in tickers:
        markup.add(types.InlineKeyboardButton(ticker, callback_data=f"ticker_{id}"))
    bot.send_message(message.chat.id, "Выберите тикер:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

def show_ticker_info(bot, call):
    ticker_id = call.data.split('_')[1]
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM tickers WHERE id = %s", (ticker_id,))
        ticker = cursor.fetchone()
        if ticker:
            _, current_rate = get_current_price(ticker[1])
            info = (
                f"<b>Тикер:</b> <code>{ticker[1]}</code>\n"
                f"<b>Точка входа (ТВХ):</b> <code>{ticker[2]}</code>\n"
                f"<b>Тейк-профит:</b> <code>{ticker[3]}</code>\n"
                f"<b>Стоп-лос:</b> <code>{ticker[4]}</code>\n"
                f"<b>Текущая стоимость:</b> <code>${current_rate}</code>\n"
                f"<b>Сетап:</b> <code>{ticker[6]}</code>\n"
                f"<b>Позиция:</b> <code>{ticker[8]}</code>"
            )
            bot.send_message(call.message.chat.id, info, parse_mode="HTML", message_thread_id=config.ALARM_THEME_ID)
            # Отправка фото сетапа, если оно доступно
            if ticker[6]:
                if os.path.exists(ticker[6]):
                    with open(ticker[6], 'rb') as photo:
                        bot.send_photo(call.message.chat.id, photo, message_thread_id=config.ALARM_THEME_ID)
                else:
                    bot.send_message(call.message.chat.id, "Фото сетапа не найдено.", message_thread_id=config.ALARM_THEME_ID)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при получении данных: {str(e)}", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()

# def show_ticker_info(bot, call):
#     ticker_id = call.data.split('_')[1]
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT * FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         if ticker:
#             _, current_rate = get_current_price(ticker[1])
#             info = (
#                 f"<b>Тикер:</b> <code>{ticker[1]}</code>\n"
#                 f"<b>Точка входа (ТВХ):</b> <code>{ticker[2]}</code>\n"
#                 f"<b>Тейк-профит:</b> <code>{ticker[3]}</code>\n"
#                 f"<b>Стоп-лос:</b> <code>{ticker[4]}</code>\n"
#                 f"<b>Текущая стоимость:</b> <code>${current_rate}</code>\n"
#                 f"<b>Сетап:</b> <code>{ticker[6]}</code>\n"
#                 f"<b>Позиция:</b> <code>{ticker[8]}</code>"
#             )
#             bot.send_message(call.message.chat.id, info, parse_mode="HTML", message_thread_id=config.ALARM_THEME_ID)
#             if ticker[6] and os.path.exists(ticker[6]):
#                 bot.send_photo(call.message.chat.id, open(ticker[6], 'rb'))
#     except Exception as e:
#         bot.send_message(call.message.chat.id, f"Failed to create chart: {str(e)}", message_thread_id=config.ALARM_THEME_ID)
#     finally:
#         cursor.close()
#         connection.close()

def delete_ticker(bot, call):
    tickers = db.get_all_tickers()
    markup = types.InlineKeyboardMarkup()
    for ticker in tickers:
        markup.add(types.InlineKeyboardButton(ticker[0], callback_data=f"del_{ticker[1]}"))
    bot.send_message(call.message.chat.id, "Выберите тикер для удаления:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

def confirm_delete_ticker(bot, call):
    parts = call.data.split("_")
    if len(parts) < 2:
        bot.send_message(call.message.chat.id, "Произошла ошибка при обработке вашего запроса.", message_thread_id=config.ALARM_THEME_ID)
        return
    ticker_id = int(parts[1])
    db.delete_ticker(ticker_id)
    bot.answer_callback_query(call.id, "Тикер удален!")
    bot.send_message(call.message.chat.id, "Тикер успешно удален.", message_thread_id=config.ALARM_THEME_ID)

def edit_ticker(bot, call):
    tickers = db.get_all_tickers()
    markup = types.InlineKeyboardMarkup()
    for ticker in tickers:
        markup.add(types.InlineKeyboardButton(ticker[0], callback_data=f"edit_{ticker[1]}"))
    bot.send_message(call.message.chat.id, "Выберите тикер для редактирования:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

def select_field_to_edit(bot, call):
    ticker_id = call.data.split("_")[1]
    markup = types.InlineKeyboardMarkup()
    fields = ["entry_point", "take_profit", "stop_loss", "current_rate", "active", "direction"]
    for field in fields:
        markup.add(types.InlineKeyboardButton(field.replace("_", " ").title(), callback_data=f"editfield_{ticker_id}_{field}"))
    bot.send_message(call.message.chat.id, "Выберите поле для редактирования:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

def get_new_value(bot, call):
    parts = call.data.split('_', 2)
    if len(parts) < 3:
        bot.send_message(call.message.chat.id, "Произошла ошибка при обработке вашего запроса.", message_thread_id=config.ALARM_THEME_ID)
        return
    _, ticker_id, field = parts
    msg = f"Введите новое значение для {field.replace('_', ' ').title()}:"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_edit"))
    bot.send_message(call.message.chat.id, msg, reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, lambda message: update_ticker_value(bot, message, ticker_id, field))

def update_ticker_value(bot, message, ticker_id, field):
    new_value = message.text
    try:
        db.update_ticker_field(ticker_id, field, new_value)
        bot.send_message(message.chat.id, f"Значение для {field.replace('_', ' ').title()} успешно обновлено!", message_thread_id=config.ALARM_THEME_ID)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при обновлении данных: {e}", message_thread_id=config.ALARM_THEME_ID)

def start_monitoring(bot):
    global global_bot
    global_bot = bot
    moscow_tz = pytz.timezone('Europe/Moscow')
    scheduler = BackgroundScheduler(timezone=moscow_tz)
    scheduler.add_job(monitor_prices, 'interval', seconds=3)
    scheduler.start()

def monitor_prices():
    logging.info("Цикл мониторинга цен...")
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, ticker, entry_point, take_profit, stop_loss FROM tickers WHERE active=1")
        tickers = cursor.fetchall()
        for ticker in tickers:
            ticker_id, ticker_name, entry_point, take_profit, stop_loss = ticker
            exchange, current_rate = get_current_price(ticker_name)
            if exchange is None or current_rate is None:
                logging.error(f"Failed to fetch current rate for {ticker_name}")
                continue
            logging.debug(f"Processing ticker {ticker_name} on {exchange}: current_rate={current_rate}")
            check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id)
    finally:
        cursor.close()
        connection.close()

def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT entry_confirmed FROM tickers WHERE id = %s", (ticker_id,))
        entry_confirmed = cursor.fetchone()[0]
        message_text = ""
        if not entry_confirmed:
            if abs(current_rate - entry_point) / entry_point < 0.015:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
                message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
                send_alert(ticker_id, message_text, reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
                return
            if not entry_confirmed and current_rate == entry_point:
                message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
                send_alert(ticker_id, message_text, reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
            return
        if current_rate >= take_profit:
            message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}."
            send_alert(ticker_id, message_text)
            db.update_ticker_active(ticker_id, False)
        if current_rate <= stop_loss:
            message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}."
            send_alert(ticker_id, message_text)
            db.update_ticker_active(ticker_id, False)
    finally:
        cursor.close()
        connection.close()

def send_alert(ticker_id, message_text, reply_markup=None):
    now = datetime.now()
    if ticker_id in last_alert_time:
        if now - last_alert_time[ticker_id] < timedelta(minutes=5):
            logging.debug(f"Alert for {ticker_id} suppressed to avoid spam.")
            return
    last_alert_time[ticker_id] = now
    logging.debug(f"Sending alert for {ticker_id}: {message_text}")
    for chat_id in config.ADMIN_CHAT_IDS:
        try:
            if reply_markup:
                global_bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup, message_thread_id=config.ALARM_THEME_ID)
            else:
                global_bot.send_message(chat_id=chat_id, text=message_text, message_thread_id=config.ALARM_THEME_ID)
            logging.info(f"Sent alert to {chat_id}: {message_text}")
        except Exception as e:
            logging.error(f"Failed to send alert to {chat_id}: {str(e)}")

def archive_and_delete_ticker(ticker_id):
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO archive SELECT * FROM tickers WHERE id = %s", (ticker_id,))
        cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
        connection.commit()
    except db.mysql.connector.Error as e:
        logging.error(f"Error during archiving/deleting ticker: {e}")
    finally:
        cursor.close()
        connection.close()

def archive_tickers_list(bot, message):
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, ticker, status FROM archive")
        tickers = cursor.fetchall()
        markup = types.InlineKeyboardMarkup()
        for id, ticker, status in tickers:
            markup.add(types.InlineKeyboardButton(f"{ticker} - {status}", callback_data=f"archive_{id}"))
        bot.send_message(message.chat.id, "Выберите сделку для просмотра:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
    except db.mysql.connector.Error as e:
        bot.send_message(message.chat.id, f"Ошибка при получении данных: {e}", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()

def show_archive_tickers_list(bot, message):
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, ticker, status FROM archive")
        tickers = cursor.fetchall()
        markup = types.InlineKeyboardMarkup()
        for id, ticker, status in tickers:
            markup.add(types.InlineKeyboardButton(f"{ticker} - {status}", callback_data=f"archive_{id}"))
        bot.send_message(message.chat.id, "Выберите сделку для просмотра:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
    except mysql.connector.Error as e:
        bot.send_message(message.chat.id, f"Ошибка при получении данных: {e}", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()
