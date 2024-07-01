# tickers.py
from telebot import types
from datetime import datetime, timedelta
from tradingview_ta import TA_Handler, Interval, Exchange
from apscheduler.schedulers.background import BackgroundScheduler
from config import PREFERRED_CHAT_ID, ALARM_CHAT_ID, ALARM_THEME_ID
from urllib.parse import urlparse
from decimal import Decimal, getcontext, ROUND_DOWN, InvalidOperation
import pytz
import config
import os
import db
import logging
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
global_bot = None

# Set the precision for Decimal
getcontext().prec = 28

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
    bot.register_next_step_handler(msg, ask_for_exchange, bot, [msg.message_id])

def ask_for_exchange(message, bot, message_ids):
    ticker_name = message.text.strip().upper()
    markup = types.InlineKeyboardMarkup()
    for exchange in EXCHANGES:
        markup.add(types.InlineKeyboardButton(exchange, callback_data=f"exchange_{exchange}_{ticker_name}"))
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    msg = bot.send_message(message.chat.id, "Выберите биржу:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
    message_ids.append(message.message_id)
    message_ids.append(msg.message_id)

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
    msg = bot.send_message(call.message.chat.id, f"Текущая цена {ticker_name} на {exchange}: {current_rate}", message_thread_id=config.ALARM_THEME_ID)
    ask_for_direction(bot, call.message, ticker_name, exchange, current_rate, [call.message.message_id, msg.message_id])

def ask_for_direction(bot, message, ticker_name, exchange, current_rate, message_ids):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Long", callback_data=f"direction_long_{ticker_name}_{exchange}_{current_rate}"),
               types.InlineKeyboardButton("Short", callback_data=f"direction_short_{ticker_name}_{exchange}_{current_rate}"))
    msg = bot.send_message(message.chat.id, "Выберите направление сделки:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
    message_ids.append(msg.message_id)

def process_direction(bot, call):
    markup = types.InlineKeyboardMarkup()
    _, direction, ticker_name, exchange, current_rate_str = call.data.split('_')
    try:
        current_rate = float(current_rate_str)
    except ValueError:
        bot.send_message(call.message.chat.id, "Ошибка при конвертации текущего курса в число.", message_thread_id=config.ALARM_THEME_ID)
        return
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
    msg = bot.send_message(call.message.chat.id, f"Введите точку входа для {ticker_name} ({direction}):", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
    bot.register_next_step_handler(call.message, process_entry_point, bot, ticker_name, exchange, direction, current_rate, [call.message.message_id, msg.message_id])

def process_entry_point(message, bot, ticker_name, exchange, direction, current_rate, message_ids):
    try:
        entry_point = Decimal(message.text)
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
        msg = bot.send_message(message.chat.id, "Введите значение тейк-профит:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
        bot.register_next_step_handler(msg, process_take_profit, bot, ticker_name, exchange, direction, entry_point, current_rate, message_ids + [message.message_id, msg.message_id])
    except InvalidOperation:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное числовое значение для точки входа.", message_thread_id=config.ALARM_THEME_ID)
        # Регистрируем тот же обработчик для повторного ввода
        bot.register_next_step_handler(message, process_entry_point, bot, ticker_name, exchange, direction, current_rate, message_ids)

def process_take_profit(message, bot, ticker_name, exchange, direction, entry_point, current_rate, message_ids):
    try:
        take_profit = Decimal(message.text)
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
        msg = bot.send_message(message.chat.id, "Введите значение стоп-лосс:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
        bot.register_next_step_handler(msg, process_stop_loss, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate, message_ids + [message.message_id, msg.message_id])
    except InvalidOperation:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное числовое значение для тейк-профит.", message_thread_id=config.ALARM_THEME_ID)
        # Регистрируем тот же обработчик для повторного ввода
        bot.register_next_step_handler(message, process_take_profit, bot, ticker_name, exchange, direction, entry_point, current_rate, message_ids)

def process_stop_loss(message, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate, message_ids):
    try:
        stop_loss = Decimal(message.text)
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_ticker"))
        msg = bot.send_message(message.chat.id, "Прикрепите изображение сетапа или отправьте URL:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
        bot.register_next_step_handler(msg, finalize_setup, bot, ticker_name, exchange, direction, entry_point, take_profit, stop_loss, current_rate, message_ids + [message.message_id, msg.message_id])
    except InvalidOperation:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное числовое значение для стоп-лосс.", message_thread_id=config.ALARM_THEME_ID)
        # Регистрируем тот же обработчик для повторного ввода
        bot.register_next_step_handler(message, process_stop_loss, bot, ticker_name, exchange, direction, entry_point, take_profit, current_rate, message_ids)

import os
from urllib.parse import urlparse

def finalize_setup(message, bot, ticker_name, exchange, direction, entry_point, take_profit, stop_loss, current_rate, message_ids):
    setup_image_path = message.text if message.content_type == 'text' else save_photo(bot, message.photo[-1].file_id)
    leverage = 10  # Плечо по умолчанию
    try:
        # Добавляем тикер в базу данных
        db.add_new_ticker(ticker_name, direction, entry_point, take_profit, stop_loss, current_rate, setup_image_path)
        
        # Расчёт потенциала
        potential = abs(Decimal(((take_profit / entry_point - 1) * leverage * 100)))
        # potential = Decimal(((take_profit / entry_point - 1) * leverage * 100))

        # Форматирование текущей стоимости с ограничением до 8 знаков после запятой
        formatted_current_rate = Decimal(current_rate).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        
        info = (
            f"─────────────────────\n"
            f"<b>🔖 Тикер:</b> <code>{ticker_name}</code>\n"
            f"─────────────────────\n"
            f"<b>🔄 Направление:</b> <code>{direction}</code>\n"
            f"<b>🎯 Точка входа (ТВХ):</b> <code>{Decimal(entry_point)}</code>\n"
            f"<b>📈 Тейк-профит:</b> <code>{Decimal(take_profit)}</code>\n"
            f"<b>📉 Стоп-лосс:</b> <code>{Decimal(stop_loss)}</code>\n"
            f"<b>💹 Текущая стоимость:</b> <code>${formatted_current_rate}</code>\n"
            # f"<b>💹 Текущая стоимость:</b> <code>${Decimal(current_rate)}</code>\n"
            f"<b>🖼 Сетап:</b> <code>{setup_image_path}</code>\n"
            f"<b>🚀 Потенциал:</b> <code>{(round(potential, 2))}%</code>\n"
            f"─────────────────────"
        )
        
        # Удаление сообщений
        for msg_id in message_ids:
            bot.delete_message(message.chat.id, msg_id)
        
        # Проверка, является ли путь изображением на диске или URL-адресом
        parsed_url = urlparse(setup_image_path)
        if setup_image_path and (os.path.exists(setup_image_path) or parsed_url.scheme in ('http', 'https')):
            if os.path.exists(setup_image_path):
                with open(setup_image_path, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption=info, parse_mode='HTML', message_thread_id=config.ALARM_THEME_ID)
            else:
                bot.send_photo(message.chat.id, setup_image_path, caption=info, parse_mode='HTML', message_thread_id=config.ALARM_THEME_ID)
        else:
            bot.send_message(message.chat.id, info, parse_mode="HTML", message_thread_id=config.ALARM_THEME_ID)
            bot.send_message(message.chat.id, "Фото сетапа не найдено.", message_thread_id=config.ALARM_THEME_ID)
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
    # Проверяем существующий тикер на всех биржах
    for exchange in EXCHANGES:
        handler.exchange = exchange
        handler.symbol = ticker_name
        try:
            analysis = handler.get_analysis()
            if analysis:
                current_rate = analysis.indicators.get("close")
                if current_rate is not None:
                    formatted_rate = Decimal(current_rate).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
                    return exchange, formatted_rate
        except Exception as e:
            logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {str(e)}")
    
    # Если тикер заканчивается на "USD" и не найден, пытаемся найти тикер с суффиксом "USDT"
    if ticker_name.endswith("USD"):
        ticker_name_usdt = ticker_name[:-3] + "USDT"  # Заменяем суффикс
        for exchange in EXCHANGES:
            handler.exchange = exchange
            handler.symbol = ticker_name_usdt
            try:
                analysis = handler.get_analysis()
                if analysis:
                    current_rate = analysis.indicators.get("close")
                    if current_rate is not None:
                        formatted_rate = Decimal(current_rate).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
                        return exchange, formatted_rate
            except Exception as e:
                logging.error(f"Error retrieving data from TradingView for {ticker_name_usdt} on {exchange}: {str(e)}")
    
    return None, None


# def get_current_price(ticker_name):
#     handler = TA_Handler(interval=Interval.INTERVAL_1_MINUTE, screener="crypto")
#     for exchange in EXCHANGES:
#         handler.exchange = exchange
#         handler.symbol = ticker_name
#         try:
#             analysis = handler.get_analysis()
#             if analysis:
#                 current_rate = analysis.indicators.get("close")
#                 if current_rate is not None:
#                     return exchange, current_rate
#         except Exception as e:
#             logging.error(f"Error retrieving data from TradingView for {ticker_name} on {exchange}: {str(e)}")
#             continue
    
    # Если не нашлось пары с суффиксом "USD", ищем с суффиксом "USDT"
    # if ticker_name.endswith("USD"):
    #     ticker_name_usdt = ticker_name + "T"
    #     for exchange in EXCHANGES:
    #         handler.exchange = exchange
    #         handler.symbol = ticker_name_usdt
    #         try:
    #             analysis = handler.get_analysis()
    #             if analysis:
    #                 current_rate = analysis.indicators.get("close")
    #                 if current_rate is not None:
    #                     return exchange, current_rate
    #         except Exception as e:
    #             logging.error(f"Error retrieving data from TradingView for {ticker_name_usdt} on {exchange}: {str(e)}")
    #             continue
    
    # logging.error(f"Failed to fetch data for {ticker_name} on all exchanges.")
    # return None, None

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
            leverage = 10
            potential = abs(Decimal(((ticker[3] / ticker[2] - 1) * leverage * 100)))

            info = (
                f"─────────────────────\n"
                f"<b>🔖 Тикер:</b> <code>{ticker[1]}</code>\n"
                f"─────────────────────\n"
                f"<b>🔄 Направление:</b> <code>{ticker[8]}</code>\n"
                f"<b>🎯 Точка входа (ТВХ):</b> <code>{Decimal(ticker[2])}</code>\n"
                f"<b>📈 Тейк-профит:</b> <code>{Decimal(ticker[3])}</code>\n"
                f"<b>📉 Стоп-лосс:</b> <code>{Decimal(ticker[4])}</code>\n"
                f"<b>💹 Текущая стоимость:</b> <code>${Decimal(current_rate)}</code>\n"
                f"<b>🚀 Потенциал:</b> <code>{round(potential, 2)}%</code>\n"
                f"─────────────────────"
            )

            parsed_url = urlparse(ticker[6])
            if ticker[6] and (os.path.exists(ticker[6]) or parsed_url.scheme in ('http', 'https')):
                if os.path.exists(ticker[6]):
                    with open(ticker[6], 'rb') as photo:
                        bot.send_photo(call.message.chat.id, photo, caption=info, parse_mode='HTML', message_thread_id=config.ALARM_THEME_ID)
                else:
                    bot.send_photo(call.message.chat.id, ticker[6], caption=info, parse_mode='HTML', message_thread_id=config.ALARM_THEME_ID)
            else:
                bot.send_message(call.message.chat.id, info, parse_mode="HTML", message_thread_id=config.ALARM_THEME_ID)
                bot.send_message(call.message.chat.id, "Фото сетапа не найдено.", message_thread_id=config.ALARM_THEME_ID)
        else:
            bot.send_message(call.message.chat.id, "Тикер не найден.", message_thread_id=config.ALARM_THEME_ID)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при получении данных: {str(e)}", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()


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
    ticker_name = db.get_ticker_name(ticker_id)
    setup_image_path = db.get_setup_image_path(ticker_id)
    
    # Удаление тикера из базы данных
    db.delete_ticker(ticker_id)
    
    # Удаление изображения, если оно существует
    if setup_image_path and os.path.exists(setup_image_path):
        os.remove(setup_image_path)
    
    bot.answer_callback_query(call.id, "Тикер удален!")
    bot.send_message(call.message.chat.id, f"Тикер {ticker_name} успешно удален.", message_thread_id=config.ALARM_THEME_ID)

# def confirm_delete_ticker(bot, call):
#     parts = call.data.split("_")
#     if len(parts) < 2:
#         bot.send_message(call.message.chat.id, "Произошла ошибка при обработке вашего запроса.", message_thread_id=config.ALARM_THEME_ID)
#         return
#     ticker_id = int(parts[1])
#     setup_image_path = db.get_setup_image_path(ticker_id)
    
#     # Удаление тикера из базы данных
#     db.delete_ticker(ticker_id)
    
#     # Удаление изображения, если оно существует
#     if setup_image_path and os.path.exists(setup_image_path):
#         os.remove(setup_image_path)
    
#     bot.answer_callback_query(call.id, "Тикер удален!")
#     bot.send_message(call.message.chat.id, "Тикер успешно удален.", message_thread_id=config.ALARM_THEME_ID)

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
    scheduler.add_job(monitor_prices, 'interval', seconds=1)
    scheduler.start()

def monitor_prices():
    logging.info("Цикл мониторинга цен...")
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, ticker, entry_point, take_profit, stop_loss, delay_until FROM tickers WHERE active=1")
        tickers = cursor.fetchall()
        for ticker in tickers:
            ticker_id, ticker_name, entry_point, take_profit, stop_loss, delay_until = ticker
            
            if delay_until and datetime.now() < delay_until:
                continue
            
            exchange, current_rate_str = get_current_price(ticker_name)
            if exchange is None or current_rate_str is None:
                logging.error(f"Failed to fetch current rate for {ticker_name}")
                continue
            try:
                current_rate = float(current_rate_str)
            except ValueError:
                logging.error(f"Invalid current rate value: {current_rate_str}")
                continue

            logging.debug(f"Processing ticker {ticker_name} on {exchange}: current_rate={current_rate}")
            check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id)
    finally:
        cursor.close()
        connection.close()

# def monitor_prices():
#     logging.info("Цикл мониторинга цен...")
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT id, ticker, entry_point, take_profit, stop_loss, delay_until FROM tickers WHERE active=1")
#         tickers = cursor.fetchall()
#         for ticker in tickers:
#             ticker_id, ticker_name, entry_point, take_profit, stop_loss, delay_until = ticker
            
#             if delay_until and datetime.now() < delay_until:
#                 continue
            
#             exchange, current_rate = get_current_price(ticker_name)
#             if exchange is None or current_rate is None:
#                 logging.error(f"Failed to fetch current rate for {ticker_name}")
#                 continue
#             logging.debug(f"Processing ticker {ticker_name} on {exchange}: current_rate={current_rate}")
#             check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id)
#     finally:
#         cursor.close()
#         connection.close()

def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
        entry_confirmed, delay_until = cursor.fetchone()

        entry_point = Decimal(entry_point)
        take_profit = Decimal(take_profit)
        stop_loss = Decimal(stop_loss)
        current_rate = Decimal(current_rate)
        
        # Проверка задержки активации тикера
        if delay_until and datetime.now() < delay_until:
            logging.debug(f"Активация тикера {ticker_name} отложена до {delay_until}")
            return

        # Проверка подтверждения входа в тикер
        if not entry_confirmed:
            if entry_point == Decimal('0'):
                logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
                return
            # Уведомление о приближении к точке входа
            if abs(current_rate - entry_point) / entry_point < Decimal('0.015'):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
                markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
                message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: `{current_rate}`)."
                send_alert(ticker_id, message_text, reply_markup=markup, parse_mode="Markdown")
                return

        # Проверка условий для тейк-профита и стоп-лосса
        if abs(current_rate - take_profit) / take_profit < Decimal('0.002'):  # Если достигнут тейк-профит
            status = "Прибыль"
            logging.debug(f"Отправка уведомления о достижении тейк-профита для {ticker_name}")
            message_text = f"🎉 {ticker_name} на бирже {exchange} достиг уровня тейк-профита: ${take_profit}."
            print(f"\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ ТП!!!!!!!!!!!!!!!!!!!!!!\n🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}.\n\n\n\n")
            send_alert(ticker_id, message_text, parse_mode="Markdown")
            db.archive_and_remove_ticker(ticker_id, current_rate, status)

        elif abs(current_rate - stop_loss) / stop_loss < Decimal('0.002'):  # Если достигнут стоп-лосс
            status = "Убыток"
            logging.debug(f"Отправка уведомления о достижении стоп-лосса для {ticker_name}")
            print(f"\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ СЛ!!!!!!!!!!!!!!!!!!!!!!\n🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}.\n\n\n\n")
            message_text = f"🛑 {ticker_name} на бирже {exchange} достиг уровня стоп-лосса: ${stop_loss}."
            send_alert(ticker_id, message_text, parse_mode="Markdown")
            db.archive_and_remove_ticker(ticker_id, current_rate, status)

    except Exception as e:
        logging.error(f"Ошибка в функции check_price_thresholds: {e}")
    finally:
        # Всегда закрываем курсор и соединение
        cursor.close()
        connection.close()

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
#         entry_confirmed, delay_until = cursor.fetchone()

#         # Преобразование значений в Decimal
#         entry_point = Decimal(entry_point)
#         take_profit = Decimal(take_profit)
#         stop_loss = Decimal(stop_loss)
#         current_rate = Decimal(current_rate)
        
#         if delay_until and datetime.now() < delay_until:
#             logging.debug(f"Ticker {ticker_name} is delayed until {delay_until}")
#             return

#         status = ""
#         logging.debug(f"Ticker {ticker_name} - current_rate: {current_rate}, take_profit: {take_profit}, stop_loss: {stop_loss}, entry_confirmed: {entry_confirmed}")

#         if not entry_confirmed:
#             if entry_point == Decimal('0'):
#                 logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
#                 return
#             if abs(current_rate - entry_point) / entry_point < Decimal('0.015'):
#                 markup = types.InlineKeyboardMarkup()
#                 markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
#                 markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
#                 message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: `{format_decimal(current_rate)}`)."
#                 send_alert(ticker_id, message_text, reply_markup=markup, parse_mode="Markdown")
#                 return
#             if not entry_confirmed:
#                 if abs(current_rate - entry_point) / entry_point < Decimal('0.002'):
#                     message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
#                     send_alert(ticker_id, message_text, reply_markup=markup)
        
#         if abs(current_rate - take_profit) / take_profit < Decimal('0.002'):
#             status = "Прибыль"
#             logging.debug(f"Sending take profit alert for {ticker_name}")
#             message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: $`{take_profit}.`"
#             send_alert(ticker_id, message_text, parse_mode="Markdown")
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)

#         elif abs(current_rate - stop_loss) / stop_loss < Decimal('0.002'):
#             status = "убыток"
#             logging.debug(f"Sending stop loss alert for {ticker_name}")
#             message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: `{stop_loss}`."
#             send_alert(ticker_id, message_text, parse_mode="Markdown")
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)

#     except Exception as e:
#         logging.error(f"Error in check_price_thresholds: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
#         entry_confirmed, delay_until = cursor.fetchone()
        
#         if delay_until and datetime.now() < delay_until:
#             logging.debug(f"Ticker {ticker_name} is delayed until {delay_until}")
#             return

#         status = ""
#         logging.debug(f"Ticker {ticker_name} - current_rate: {current_rate}, take_profit: {take_profit}, stop_loss: {stop_loss}, entry_confirmed: {entry_confirmed}")

#         if not entry_confirmed:
#             if entry_point == 0:
#                 logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
#                 return
#             if abs(current_rate - entry_point) / entry_point < 0.015:
#                 markup = types.InlineKeyboardMarkup()
#                 markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
#                 markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
#                 message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#                 return
#             if not entry_confirmed:
#                 if abs(current_rate - entry_point) / entry_point < 0.002:
#                     message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
#                     send_alert(ticker_id, message_text, reply_markup=markup)
        
#         if abs(current_rate - take_profit) / take_profit < 0.002:  # Используем диапазон в 0.2% от тейк-профита
#             status = "прибыль"
#             logging.debug(f"Sending take profit alert for {ticker_name}")
#             print(f"\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ ТП!!!!!!!!!!!!!!!!!!!!!!\n🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}.\n\n\n\n")
#             message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}.\nfrom tickers.py"
#             send_alert(ticker_id, message_text)
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#         elif abs(current_rate - stop_loss) / stop_loss < 0.002:  # Используем диапазон в 0.2% от стоп-лосса
#             status = "убыток"
#             logging.debug(f"Sending stop loss alert for {ticker_name}")
#             message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}.\nfrom tickers.py"
#             print(f"\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ СЛ!!!!!!!!!!!!!!!!!!!!!!\n🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}.\n\n\n\n")
#             send_alert(ticker_id, message_text)
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#     except Exception as e:
#         logging.error(f"Error in check_price_thresholds: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
#         entry_confirmed, delay_until = cursor.fetchone()
        
#         if delay_until and datetime.now() < delay_until:
#             logging.debug(f"Ticker {ticker_name} is delayed until {delay_until}")
#             return

#         # message_text = ""
#         status = ""
#         logging.debug(f"Ticker {ticker_name} - current_rate: {current_rate}, take_profit: {take_profit}, stop_loss: {stop_loss}, entry_confirmed: {entry_confirmed}")

#         if not entry_confirmed:
#             if entry_point == 0:
#                 logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
#                 return
#             if abs(current_rate - entry_point) / entry_point < 0.015:
#                 markup = types.InlineKeyboardMarkup()
#                 markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
#                 markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
#                 message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#                 return
#             if not entry_confirmed:
#                 if abs(current_rate - entry_point) / entry_point < 0.002:
#                     message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
#                     send_alert(ticker_id, message_text, reply_markup=markup)
#             # return
#         if abs(current_rate - take_profit) / take_profit < 0.002:  # Используем диапазон в 0.2% от тейк-профита
#             message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}."
#             status = "прибыль"
#             logging.debug(f"Sending take profit alert for {ticker_name}")
#             send_alert(ticker_id, f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}.")
#             print(f"\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ ТП!!!!!!!!!!!!!!!!!!!!!!\n\n\n\n{ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}")
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#         elif abs(current_rate - stop_loss) / stop_loss < 0.002:  # Используем диапазон в 0.2% от стоп-лосса
#             message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}."
#             print(f"\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ СЛ!!!!!!!!!!!!!!!!!!!!!!\n\n\n\n🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}.")
#             status = "убыток"
#             logging.debug(f"Sending stop loss alert for {ticker_name}")
#             send_alert(ticker_id, f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}.")
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#     except Exception as e:
#         logging.error(f"Error in check_price_thresholds: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
#         entry_confirmed, delay_until = cursor.fetchone()
        
#         if delay_until and datetime.now() < delay_until:
#             logging.debug(f"Ticker {ticker_name} is delayed until {delay_until}")
#             return

#         message_text = ""
#         status = ""
#         logging.debug(f"Ticker {ticker_name} - current_rate: {current_rate}, take_profit: {take_profit}, stop_loss: {stop_loss}, entry_confirmed: {entry_confirmed}")

#         if not entry_confirmed:
#             if entry_point == 0:
#                 logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
#                 return
#             if abs(current_rate - entry_point) / entry_point < 0.015:
#                 markup = types.InlineKeyboardMarkup()
#                 markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
#                 markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
#                 message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#                 return
#             if not entry_confirmed and current_rate == entry_point:
#                 message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#             # return
#         if current_rate == take_profit:
#             message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}."
#             status = "прибыль"
#             logging.debug(f"Sending take profit alert for {ticker_name}")
#             send_alert(ticker_id, message_text)
#             print("\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ ТП!!!!!!!!!!!!!!!!!!!!!!\n\n\n\n")
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#         elif current_rate == stop_loss:
#             message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}."
#             print("\n\n\n\n!!!!!!!!!!!!!!!!РАБОТАЕТ СЛ!!!!!!!!!!!!!!!!!!!!!!\n\n\n\n")
#             status = "убыток"
#             logging.debug(f"Sending stop loss alert for {ticker_name}")
#             send_alert(ticker_id, message_text)
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#     except Exception as e:
#         logging.error(f"Error in check_price_thresholds: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
#         entry_confirmed, delay_until = cursor.fetchone()
        
#         if delay_until and datetime.now() < delay_until:
#             return

#         message_text = ""
#         status = ""
#         logging.debug(f"Ticker {ticker_name} - current_rate: {current_rate}, take_profit: {take_profit}, stop_loss: {stop_loss}, entry_confirmed: {entry_confirmed}")

#         if not entry_confirmed:
#             if entry_point == 0:
#                 logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
#                 return
#             if abs(current_rate - entry_point) / entry_point < 0.015:
#                 markup = types.InlineKeyboardMarkup()
#                 markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
#                 markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
#                 message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#                 return
#             if not entry_confirmed and current_rate == entry_point:
#                 message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#             return
#         if current_rate >= take_profit:
#             message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}."
#             status = "прибыль"
#             logging.debug(f"Sending take profit alert for {ticker_name}")
#             send_alert(ticker_id, message_text)
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#         elif current_rate <= stop_loss:
#             message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}."
#             status = "убыток"
#             logging.debug(f"Sending stop loss alert for {ticker_name}")
#             send_alert(ticker_id, message_text)
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#     finally:
#         cursor.close()
#         connection.close()

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
#         entry_confirmed, delay_until = cursor.fetchone()
        
#         if delay_until and datetime.now() < delay_until:
#             return

#         message_text = ""
#         status = ""
#         if not entry_confirmed:
#             if entry_point == 0:
#                 logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
#                 return
#             if abs(current_rate - entry_point) / entry_point < 0.015:
#                 markup = types.InlineKeyboardMarkup()
#                 markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
#                 markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
#                 message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#                 return
#             if not entry_confirmed and current_rate == entry_point:
#                 message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#             return
#         if current_rate >= take_profit:
#             message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}."
#             status = "прибыль"
#             send_alert(ticker_id, message_text)
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#         elif current_rate <= stop_loss:
#             message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}."
#             status = "убыток"
#             send_alert(ticker_id, message_text)
#             db.archive_and_remove_ticker(ticker_id, current_rate, status)
#     finally:
#         cursor.close()
#         connection.close()

# def check_price_thresholds(ticker_name, exchange, entry_point, take_profit, stop_loss, current_rate, ticker_id):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT entry_confirmed, delay_until FROM tickers WHERE id = %s", (ticker_id,))
#         entry_confirmed, delay_until = cursor.fetchone()
        
#         if delay_until and datetime.now() < delay_until:
#             return

#         message_text = ""
#         if not entry_confirmed:
#             if entry_point == 0:
#                 logging.error(f"Точка входа для {ticker_name} равна нулю, проверка будет пропущена...")
#                 return
#             if abs(current_rate - entry_point) / entry_point < 0.015:
#                 markup = types.InlineKeyboardMarkup()
#                 markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
#                 markup.add(types.InlineKeyboardButton("Заглушить уведомления", callback_data=f"mute_entry_{ticker_id}"))
#                 message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#                 return
#             if not entry_confirmed and current_rate == entry_point:
#                 message_text = f"✅ {ticker_name} достиг точки входа на {exchange}.\n"
#                 send_alert(ticker_id, message_text, reply_markup=markup)
#             return
#         if current_rate >= take_profit:
#             message_text = f"🎉 {ticker_name} на {exchange} достиг уровня тейк-профита: {take_profit}."
#             send_alert(ticker_id, message_text)
#             db.update_ticker_active(ticker_id, False)
#         if current_rate <= stop_loss:
#             message_text = f"🛑 {ticker_name} на {exchange} достиг уровня стоп-лосса: {stop_loss}."
#             send_alert(ticker_id, message_text)
#             db.update_ticker_active(ticker_id, False)
#     finally:
#         cursor.close()
#         connection.close()

def send_alert(ticker_id, message_text, reply_markup=None, parse_mode=None):
    if ticker_id in last_alert_time and (datetime.now() - last_alert_time[ticker_id] < timedelta(minutes=5)):
        logging.debug(f"Alert for {ticker_id} suppressed to avoid spam.")
        return

    last_alert_time[ticker_id] = datetime.now()
    chat_id = config.ALARM_CHAT_ID
    try:
        if reply_markup:
            global_bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup, message_thread_id=config.ALARM_THEME_ID, parse_mode=parse_mode)
        else:
            global_bot.send_message(chat_id=chat_id, text=message_text, message_thread_id=config.ALARM_THEME_ID, parse_mode=parse_mode)
        logging.info(f"Alert sent to {chat_id}: {message_text}")
    except Exception as e:
        logging.error(f"Failed to send alert to {chat_id}: {str(e)}")

# def send_alert(ticker_id, message_text, reply_markup=None):
#     now = datetime.now()
#     if ticker_id in last_alert_time:
#         if now - last_alert_time[ticker_id] < timedelta(minutes=5):
#             logging.debug(f"Alert for {ticker_id} suppressed to avoid spam.")
#             return
#     last_alert_time[ticker_id] = now
#     logging.debug(f"Sending alert for {ticker_id}: {message_text}")
#     chat_id = config.ALARM_CHAT_ID
#     try:
#         if reply_markup:
#             global_bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup, message_thread_id=config.ALARM_THEME_ID)
#         else:
#             global_bot.send_message(chat_id=chat_id, text=message_text, message_thread_id=config.ALARM_THEME_ID)
#         logging.info(f"Sent alert to {chat_id}: {message_text}")
#     except Exception as e:
#         if "message thread not found" in str(e):
#             logging.error(f"Failed to send alert to {chat_id}: {str(e)}. Check if the thread exists.")
#         elif "group chat was upgraded to a supergroup chat" in str(e):
#             logging.error(f"Failed to send alert to {chat_id}: {str(e)}. The group chat was upgraded to a supergroup chat.")
#         else:
#             logging.error(f"Failed to send alert to {chat_id}: {str(e)}")

def mute_entry(bot, call):
    ticker_id = int(call.data.split('_')[2])
    markup = types.InlineKeyboardMarkup()
    intervals = [("15 минут", 15), ("30 минут", 30), ("1 час", 60), ("4 часа", 240), ("8 часов", 480), ("12 часов", 720)]
    for label, minutes in intervals:
        markup.add(types.InlineKeyboardButton(label, callback_data=f"set_mute_{ticker_id}_{minutes}"))
    bot.send_message(call.message.chat.id, "На сколько заглушить уведомление?", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

def set_mute(bot, call):
    parts = call.data.split('_')
    ticker_id = int(parts[2])
    minutes = int(parts[3])
    delay_until = datetime.now() + timedelta(minutes=minutes)
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE tickers SET delay_until = %s WHERE id = %s", (delay_until, ticker_id))
        connection.commit()
        bot.send_message(call.message.chat.id, f"Уведомление заглушено на {minutes} минут.", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()

def set_mute(bot, call):
    parts = call.data.split('_')
    ticker_id = int(parts[2])
    minutes = int(parts[3])
    delay_until = datetime.now() + timedelta(minutes=minutes)
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE tickers SET delay_until = %s WHERE id = %s", (delay_until, ticker_id))
        cursor.execute("SELECT ticker FROM tickers WHERE id = %s", (ticker_id,))
        ticker_name = cursor.fetchone()[0]
        connection.commit()
        bot.send_message(call.message.chat.id, f"Уведомление для тикера {ticker_name} заглушено на {minutes} минут.", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()


def set_mute(bot, call):
    parts = call.data.split('_')
    ticker_id = int(parts[2])
    minutes = int(parts[3])
    delay_until = datetime.now() + timedelta(minutes=minutes)
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE tickers SET delay_until = %s WHERE id = %s", (delay_until, ticker_id))
        cursor.execute("SELECT ticker FROM tickers WHERE id = %s", (ticker_id,))
        ticker_name = cursor.fetchone()[0]
        connection.commit()
        bot.send_message(call.message.chat.id, f"Уведомление для тикера {ticker_name} заглушено на {minutes} минут.", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()


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
        if not tickers:
            bot.send_message(ALARM_CHAT_ID, "Архив пуст.", message_thread_id=ALARM_THEME_ID)
            return
        
        markup = types.InlineKeyboardMarkup()
        for id, ticker, status in tickers:
            markup.add(types.InlineKeyboardButton(f"{ticker} - {status}", callback_data=f"archive_{id}"))
        markup.add(types.InlineKeyboardButton("Очистить архив", callback_data="clear_all_archive"))
        markup.add(types.InlineKeyboardButton("Удалить тикер", callback_data="selective_delete_trades"))

        bot.send_message(ALARM_CHAT_ID, "Выберите сделку для просмотра:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
    except mysql.connector.Error as e:
        bot.send_message(ALARM_CHAT_ID, f"Ошибка при получении данных: {e}", message_thread_id=ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()

# def show_archive_tickers_list(bot, message):
#     connection = db.get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT id, ticker, status FROM archive")
#         tickers = cursor.fetchall()
#         markup = types.InlineKeyboardMarkup()
#         for id, ticker, status in tickers:
#             markup.add(types.InlineKeyboardButton(f"{ticker} - {status}", callback_data=f"archive_{id}"))
#         bot.send_message(message.chat.id, "Выберите сделку для просмотра:", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)
#     except mysql.connector.Error as e:
#         bot.send_message(message.chat.id, f"Ошибка при получении данных: {e}", message_thread_id=config.ALARM_THEME_ID)
#     finally:
#         cursor.close()
#         connection.close()

# Отложить сделку
import re

def delay_entry(bot, call):
    ticker_id = int(call.data.split('_')[2])
    msg = bot.send_message(call.message.chat.id, "На какое время отложим вход в сделку?\nПримеры: 30 min, 1h, 1 day, 22 минуты", message_thread_id=config.ALARM_THEME_ID)
    bot.register_next_step_handler(msg, lambda message: process_delay_entry(bot, message, ticker_id))

def process_delay_entry(bot, message, ticker_id):
    time_str = message.text.strip().lower()
    
    match = re.match(r'(\d+)\s*(секунд|сек|s|seconds|second|минуты|мин|m|minutes|minute|часы|час|ч|h|hours|hour|дни|день|д|day|days|d)', time_str)
    if not match:
        bot.send_message(message.chat.id, "Неправильный формат. Пожалуйста, используйте допустимые форматы времени, например: 30 сек, 1 мин, 1 час, 1 день", message_thread_id=config.ALARM_THEME_ID)
        return
    
    delay_value = int(match.group(1))
    delay_unit = match.group(2)

    delay_map = {
        'секунд': 'seconds', 'сек': 'seconds', 's': 'seconds', 'seconds': 'seconds', 'second': 'seconds',
        'минуты': 'minutes', 'мин': 'minutes', 'm': 'minutes', 'minutes': 'minutes', 'minute': 'minutes',
        'часы': 'hours', 'час': 'hours', 'ч': 'hours', 'h': 'hours', 'hours': 'hours', 'hour': 'hours',
        'дни': 'days', 'день': 'days', 'д': 'days', 'day': 'days', 'days': 'days', 'd': 'days'
    }
    
    delay_time = timedelta(**{delay_map[delay_unit]: delay_value})
    delay_until = datetime.now() + delay_time

    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE tickers SET delay_until = %s WHERE id = %s", (delay_until, ticker_id))
        connection.commit()
        bot.send_message(message.chat.id, f"Вход в сделку отложен на {delay_value} {delay_unit}.", message_thread_id=config.ALARM_THEME_ID)
        schedule_delay_check(bot, ticker_id, delay_until)
    except mysql.connector.Error as e:
        bot.send_message(message.chat.id, f"Ошибка при отложении входа в сделку: {e}", message_thread_id=config.ALARM_THEME_ID)
    finally:
        cursor.close()
        connection.close()

def schedule_delay_check(bot, ticker_id, delay_until):
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Moscow'))
    scheduler.add_job(lambda: delay_check(bot, ticker_id), 'date', run_date=delay_until)
    scheduler.start()

def delay_check(bot, ticker_id):
    connection = db.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT ticker, entry_point FROM tickers WHERE id = %s", (ticker_id,))
        ticker = cursor.fetchone()
        if ticker:
            ticker_name, entry_point = ticker
            exchange, current_rate = get_current_price(ticker_name)
            if exchange and current_rate:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Подтвердить вход", callback_data=f"confirm_entry_{ticker_id}"))
                markup.add(types.InlineKeyboardButton("Отложить сделку", callback_data=f"delay_entry_{ticker_id}"))
                message_text = f"🚨 {ticker_name} находится в пределах 1.5% от точки входа: {entry_point} (текущая цена: {current_rate})."
                send_alert(ticker_id, message_text, reply_markup=markup)
    finally:
        cursor.close()
        connection.close()

# Удаление всех тикеров из архива
def delete_all_archive_trades(bot, call):
    # Получение всех изображений перед очисткой архива
    image_paths = db.get_all_archive_image_paths()
    for path in image_paths:
        if path and os.path.exists(path):
            os.remove(path)
    
    # Удаление всех записей из архива
    db.delete_all_archived_trades()
    bot.answer_callback_query(call.id, "Архив сделок полностью очищен.")
    bot.send_message(ALARM_CHAT_ID, "Все сделки из архива удалены.", message_thread_id=ALARM_THEME_ID)
