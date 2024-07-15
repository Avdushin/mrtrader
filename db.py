import mysql.connector
from datetime import datetime
from config import DB_CONFIG, ADMIN_IDS, IMAGE_UPLOAD_PATH
from decimal import Decimal, ROUND_DOWN
import config
import logging, os

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def setup_database():
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT UNIQUE
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticker VARCHAR(35),
            entry_point DECIMAL(20,10),
            take_profit DECIMAL(20,10),
            stop_loss DECIMAL(20,10),
            current_rate DECIMAL(20,10),
            setup_image_path VARCHAR(255),
            active BOOLEAN DEFAULT TRUE,
            direction VARCHAR(10),
            entry_confirmed BOOLEAN DEFAULT FALSE,
            delay_until DATETIME DEFAULT NULL
        )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archive (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(35),
                entry_point DECIMAL(20,10),
                take_profit DECIMAL(20,10),
                stop_loss DECIMAL(20,10),
                current_rate DECIMAL(20,10),
                setup_image_path VARCHAR(255),
                direction VARCHAR(10),
                close_date DATETIME,
                status VARCHAR(10)
            )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chat_id BIGINT UNIQUE
        )
       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_themes (
            user_id BIGINT UNIQUE,
            theme VARCHAR(255),
            PRIMARY KEY(user_id)
        );
       ''')
                
        for admin_id in ADMIN_IDS:
            cursor.execute("INSERT IGNORE INTO admins (user_id) VALUES (%s)", (admin_id,))
        db.commit()
    except mysql.connector.Error as err:
        print("Ошибка при работе с MySQL:", err)
    finally:
        cursor.close()
        db.close()

def set_user_theme(user_id, theme):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO user_themes (user_id, theme) VALUES (%s, %s) ON DUPLICATE KEY UPDATE theme = %s", (user_id, theme, theme))
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def get_user_theme(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT theme FROM user_themes WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()

def add_admin(user_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO admins (user_id) VALUES (%s)", (user_id,))
        db.commit()
    finally:
        cursor.close()
        db.close()

def remove_admin(user_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM admins WHERE user_id = %s", (user_id,))
        db.commit()
    finally:
        cursor.close()
        db.close()

def is_admin(user_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM admins WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()[0]
        return result > 0
    finally:
        cursor.close()
        db.close()

def get_admins():
    env_admins = set(config.ADMIN_IDS)
    db_admins = set()
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM admins")
            for row in cursor:
                db_admins.add(row[0])
    finally:
        if connection:
            connection.close()
    return list(env_admins.union(db_admins))

from decimal import Decimal

def add_new_ticker(ticker_name, direction, entry_point, take_profit, stop_loss, current_rate, setup_image_path):
    entry_point = Decimal(entry_point)
    take_profit = Decimal(take_profit)
    stop_loss = Decimal(stop_loss)
    current_rate = Decimal(current_rate)

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
        INSERT INTO tickers (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error inserting data: {e}")
    finally:
        cursor.close()
        connection.close()

def get_all_tickers():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT ticker, id FROM tickers")
        tickers = cursor.fetchall()
        return tickers
    finally:
        cursor.close()
        connection.close()

def get_ticker_name(ticker_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT ticker FROM tickers WHERE id = %s", (ticker_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    finally:
        cursor.close()
        connection.close()

def delete_ticker(ticker_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT setup_image_path FROM tickers WHERE id = %s", (ticker_id,))
        setup_image_path = cursor.fetchone()
        if setup_image_path and os.path.exists(setup_image_path[0]):
            os.remove(setup_image_path[0])

        cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error deleting ticker: {e}")
    finally:
        cursor.close()
        connection.close()

def get_setup_image_path(ticker_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT setup_image_path FROM tickers WHERE id = %s", (ticker_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    finally:
        cursor.close()
        connection.close()

def update_ticker(ticker_id, field, new_value):
    connection = get_db_connection()
    cursor = connection.cursor()
    query = f"UPDATE tickers SET {field} = %s WHERE id = %s"
    try:
        cursor.execute(query, (new_value, ticker_id))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error updating ticker: {e}")
    finally:
        cursor.close()
        connection.close()

def update_ticker_field(ticker_id, field, new_value):
    connection = get_db_connection()
    cursor = connection.cursor()
    query = f"UPDATE tickers SET {field} = %s WHERE id = %s"
    try:
        cursor.execute(query, (new_value, ticker_id))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error updating ticker: {e}")
    finally:
        cursor.close()
        connection.close()

def update_ticker_active(ticker_id, active_status):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE tickers SET active = %s WHERE id = %s", (int(active_status), ticker_id))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error updating ticker active status: {e}")
    finally:
        cursor.close()
        connection.close()

def confirm_entry(ticker_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE tickers SET entry_confirmed = TRUE WHERE id = %s", (ticker_id,))
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def get_active_trades():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, ticker, entry_point, take_profit, stop_loss, current_rate, direction, entry_confirmed
            FROM tickers
            WHERE entry_confirmed = TRUE
        """)
        trades = cursor.fetchall()
        return [{
            'id': trade[0],
            'ticker': trade[1],
            'entry_point': trade[2],
            'take_profit': trade[3],
            'stop_loss': trade[4],
            'current_rate': trade[5],
            'direction': trade[6],
            'entry_confirmed': trade[7]
        } for trade in trades]
    finally:
        cursor.close()
        connection.close()

def cancel_trade(trade_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        logging.info(f"Cancelling trade with ID: {trade_id}")
        cursor.execute("UPDATE tickers SET entry_confirmed = FALSE WHERE id = %s", (trade_id,))
        connection.commit()
        logging.info(f"Trade with ID: {trade_id} has been cancelled.")
    except mysql.connector.Error as e:
        logging.error(f"Error cancelling trade: {e}")
    finally:
        cursor.close()
        connection.close()

def get_trade_details(trade_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, ticker, entry_point, take_profit, stop_loss, current_rate, direction, active, setup_image_path, entry_confirmed
            FROM tickers
            WHERE id = %s
        """, (trade_id,))
        trade = cursor.fetchone()
        return {
            'id': trade[0],
            'ticker': trade[1],
            'entry_point': trade[2],
            'take_profit': trade[3],
            'stop_loss': trade[4],
            'current_rate': trade[5],
            'direction': trade[6],
            'active': trade[7],
            'setup_image_path': trade[8],
            'entry_confirmed': trade[9]
        } if trade else None
    finally:
        cursor.close()
        connection.close()

def get_ticker_by_name(ticker_name):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM tickers WHERE ticker = %s", (ticker_name,))
        ticker = cursor.fetchone()
        return {
            'id': ticker[0],
            'ticker': ticker[1],
            'entry_point': ticker[2],
            'take_profit': ticker[3],
            'stop_loss': ticker[4],
            'current_rate': ticker[5],
            'setup_image_path': ticker[6],
            'active': ticker[7],
            'direction': ticker[8],
            'entry_confirmed': ticker[9]
        } if ticker else None
    except mysql.connector.Error as e:
        print(f"Error retrieving ticker by name: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def archive_tickers():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM tickers WHERE active = 0")
        tickers = cursor.fetchall()
        logging.debug(f"Archiving tickers: {tickers}") 

        for ticker in tickers:
            id, ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, active, direction, _ = ticker

            status = "прибыль" if current_rate >= take_profit else "убыток"
            close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))

            cursor.execute("DELETE FROM tickers WHERE id = %s", (id,))

        connection.commit()
    except mysql.connector.Error as e:
        logging.error(f"Ошибка при архивации тикеров: {e}")
    finally:
        cursor.close()
        connection.close()

# If prod don't work
# def archive_and_remove_ticker(ticker_id, current_rate, status, bot):
#     from tickers import send_profit_loss_alert
    
#     connection = get_db_connection()
#     cursor = connection.cursor()

#     try:
#         logging.debug(f"Attempting to fetch ticker data for ID {ticker_id}")
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction, exchange FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()

#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction, exchange = ticker
#             logging.info(f"Fetched data for ticker ID {ticker_id}: {ticker}")

#             # Применение Decimal для точных расчётов и форматирование вывода
#             entry_point = Decimal(entry_point)
#             take_profit = Decimal(take_profit).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
#             stop_loss = Decimal(stop_loss).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
#             current_rate = Decimal(current_rate).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#             logging.debug(f"Inserting into archive for ticker ID {ticker_id}")
#             cursor.execute("""
#                 INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))

#             message_text = f"{'🎉' if status == 'прибыль' else '🛑'} {ticker_name} на бирже {exchange} достиг уровня {'тейк-профита' if status == 'прибыль' else 'стоп-лосса'}: <code>{(take_profit if status == 'прибыль' else stop_loss)}</code>."
#             send_profit_loss_alert(bot, ticker_id, ticker_name, direction, entry_point, (take_profit if status == 'прибыль' else stop_loss), current_rate, message_text, status)
#             logging.info(f"Sent notification for {ticker_name} with status: {status}")

#             logging.debug(f"Setting ticker ID {ticker_id} to inactive and deleting")
#             cursor.execute("UPDATE tickers SET active = 0 WHERE id = %s", (ticker_id,))
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#             connection.commit()
#     except Exception as e:
#         logging.error(f"Error archiving and deleting ticker {ticker_id}: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# Prod
def archive_and_remove_ticker(ticker_id, current_rate, status, bot):
    from tickers import send_profit_loss_alert

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction, exchange FROM tickers WHERE id = %s", (ticker_id,))
        ticker = cursor.fetchone()
        logging.debug(f"Fetched ticker data for ID {ticker_id}: {ticker}")

        if ticker:
            ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction, exchange = ticker

            # Конвертация данных в Decimal и форматирование вывода
            entry_point = Decimal(entry_point).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            take_profit = Decimal(take_profit).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            stop_loss = Decimal(stop_loss).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            current_rate = Decimal(current_rate).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)

            close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Проверка достижения уровней и отправка соответствующих уведомлений
            if status == 'прибыль':
                message_text = f"🎉 {ticker_name} на бирже {exchange} достиг уровня тейк-профита: <code>{take_profit}</code>."
            else:
                message_text = f"🛑 {ticker_name} на бирже {exchange} достиг уровня стоп-лосса: <code>{stop_loss}</code>."
            send_profit_loss_alert(bot, ticker_id, ticker_name, direction, entry_point, (take_profit if status == 'прибыль' else stop_loss), current_rate, message_text, status)

            # Архивация данных тикера
            cursor.execute("""
                INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
            logging.debug(f"Archived {ticker_name} with status {status}")

            # Удаление тикера из активной таблицы
            cursor.execute("UPDATE tickers SET active = 0 WHERE id = %s", (ticker_id,))
            cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
            connection.commit()
    except Exception as e:
        logging.error(f"Error archiving and deleting ticker {ticker_id}: {e}")
    finally:
        cursor.close()
        connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status, bot):
#     from tickers import send_profit_loss_alert
    
#     connection = get_db_connection()
#     cursor = connection.cursor()

#     try:
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         logging.debug(f"Fetched ticker data for ID {ticker_id}: {ticker}")

#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker

#             # Применение Decimal для точных расчётов и форматирование вывода
#             entry_point = Decimal(entry_point)
#             take_profit = Decimal(take_profit).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
#             stop_loss = Decimal(stop_loss).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
#             current_rate = Decimal(current_rate).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#             cursor.execute("""
#                 INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             logging.debug(f"Archived {ticker_name} with status {status}")

#             # Форматирование сообщения с учётом количества знаков после запятой
#             message_text = f"{'🎉' if status == 'прибыль' else '🛑'} {ticker_name} достиг уровня {'тейк-профита' if status == 'прибыль' else 'стоп-лосса'}: <code>{current_rate}</code>."
#             send_profit_loss_alert(bot, ticker_id, ticker_name, direction, entry_point, take_profit, current_rate, message_text, status)

#             cursor.execute("UPDATE tickers SET active = 0 WHERE id = %s", (ticker_id,))
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#             connection.commit()
#     except Exception as e:
#         logging.error(f"Error archiving and deleting ticker {ticker_id}: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status, bot):
#     from tickers import send_profit_loss_alert
    
#     # Получаем соединение с базой данных
#     connection = get_db_connection()
#     cursor = connection.cursor()

#     try:
#         # Получаем данные о тикере из таблицы tickers по его ID
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         logging.debug(f"Fetched ticker data for ID {ticker_id}: {ticker}")

#         if ticker:
#             # Разбор полученных данных
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker

#             # Конвертация данных в Decimal для точности расчётов
#             entry_point = Decimal(entry_point)
#             take_profit = Decimal(take_profit)
#             stop_loss = Decimal(stop_loss)
#             current_rate = Decimal(current_rate)

#             # Форматирование даты закрытия сделки
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#             # Вставка данных в таблицу archive
#             cursor.execute("""
#                 INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             logging.debug(f"Archived {ticker_name} with status {status}")

#             # Отправка уведомления через бота
#             message_text = f"{'🎉' if status == 'прибыль' else '🛑'} {ticker_name} достиг уровня {'тейк-профита' if status == 'прибыль' else 'стоп-лосса'}: <code>{current_rate}</code>."
#             send_profit_loss_alert(bot, ticker_id, ticker_name, direction, entry_point, take_profit, current_rate, message_text, status)
#             logging.debug(f"Notification sent for {ticker_name} status: {status}")

#             # Перевод тикера в неактивное состояние и его удаление из таблицы tickers
#             cursor.execute("UPDATE tickers SET active = 0 WHERE id = %s", (ticker_id,))
#             logging.debug(f"Ticker {ticker_id} set to inactive")
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#             logging.debug(f"Ticker {ticker_id} deleted from tickers table")

#             # Фиксация изменений в базе данных
#             connection.commit()
#     except Exception as e:
#         # Логирование ошибок при возникновении исключений
#         logging.error(f"Error archiving and deleting ticker {ticker_id}: {e}")
#     finally:
#         # Гарантированное закрытие курсора и соединения с базой
#         cursor.close()
#         connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status):
#     from tickers import send_alert
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker
#             entry_point = Decimal(entry_point)
#             take_profit = Decimal(take_profit)
#             stop_loss = Decimal(stop_loss)
#             current_rate = Decimal(current_rate)
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             cursor.execute("""
#             INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             connection.commit()
#             logging.debug(f"Attempting to delete ticker ID: {ticker_id}")
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#             connection.commit()
#             logging.debug(f"Ticker {ticker_name} archived with status {status}")
#             # Send alert after archiving
#             message_text = f"{'🎉' if status == 'прибыль' else '🛑'} {ticker_name} достиг уровня {'тейк-профита' if status == 'прибыль' else 'стоп-лосса'}: {current_rate}."
#             send_alert(ticker_id, message_text)
#         connection.commit()
#         return
#     except Exception as e:
#         logging.error(f"Error archiving and deleting ticker: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status):
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         # Предполагаем, что данные уже извлечены и обработаны
#         logging.debug(f"Attempting to delete ticker ID: {ticker_id}")
#         cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#         connection.commit()
#         logging.debug(f"Ticker ID: {ticker_id} successfully deleted")
#     except Exception as e:
#         logging.error(f"Error deleting ticker ID: {ticker_id}: {str(e)}")
#     finally:
#         cursor.close()
#         connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status):
#     from tickers import send_alert
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             cursor.execute("""
#             INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#             logging.debug(f"Ticker {ticker_name} archived with status {status}")
#             # Send alert after archiving
#             message_text = f"{'🎉' if status == 'прибыль' else '🛑'} {ticker_name} достиг уровня {'тейк-профита' if status == 'прибыль' else 'стоп-лосса'}: {current_rate}."
#             send_alert(ticker_id, message_text)
#         connection.commit()
#         return
#     except Exception as e:
#         logging.error(f"Error archiving and deleting ticker: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status):
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             cursor.execute("""
#             INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#             logging.debug(f"Ticker {ticker_name} archived with status {status}")
#         connection.commit()
#     except Exception as e:
#         logging.error(f"Error archiving and deleting ticker: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status):
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             cursor.execute("""
#             INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#         connection.commit()
#     except mysql.connector.Error as e:
#         logging.error(f"Error archiving and deleting ticker: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def archive_and_remove_ticker(ticker_id, current_rate, status):
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             cursor.execute("""
#             INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#         connection.commit()
#     except mysql.connector.Error as e:
#         print(f"Error archiving and deleting ticker: {e}")
#     finally:
#         cursor.close()
#         connection.close()

def delete_archived_trade(trade_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT setup_image_path FROM archive WHERE id = %s", (trade_id,))
        setup_image_path = cursor.fetchone()
        if setup_image_path and os.path.exists(setup_image_path[0]):
            os.remove(setup_image_path[0])
            
        cursor.execute("DELETE FROM archive WHERE id = %s", (trade_id,))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error deleting archived trade: {e}")
    finally:
        cursor.close()
        connection.close()

def delete_all_archived_trades():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT setup_image_path FROM archive")
        paths = cursor.fetchall()
        for path in paths:
            if path[0] and os.path.exists(path[0]):
                os.remove(path[0])

        cursor.execute("DELETE FROM archive")
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error deleting all archived trades: {e}")
    finally:
        cursor.close()
        connection.close()

def get_archive_setup_image_path(trade_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT setup_image_path FROM archive WHERE id = %s", (trade_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    finally:
        cursor.close()
        connection.close()

def get_all_archive_image_paths():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT setup_image_path FROM archive")
        results = cursor.fetchall()
        return [result[0] for result in results]
    finally:
        cursor.close()
        connection.close()

def get_all_chats():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT chat_id FROM chats")
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

def add_chat_to_db(chat_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO chats (chat_id) VALUES (%s)", (chat_id,))
        db.commit()
    finally:
        cursor.close()
        db.close()

def remove_chat_from_db(chat_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM chats WHERE chat_id = %s", (chat_id,))
        db.commit()
    finally:
        cursor.close()
        db.close()
