# db.py
import mysql.connector
from datetime import datetime
from config import DB_CONFIG, ADMIN_IDS, IMAGE_UPLOAD_PATH
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
            entry_point DOUBLE,
            take_profit DOUBLE,
            stop_loss DOUBLE,
            current_rate DOUBLE,
            setup_image_path VARCHAR(255),
            active BOOLEAN DEFAULT TRUE,
            direction VARCHAR(10),
            entry_confirmed BOOLEAN DEFAULT FALSE
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS archive (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticker VARCHAR(35),
            entry_point DOUBLE,
            take_profit DOUBLE,
            stop_loss DOUBLE,
            current_rate DOUBLE,
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
                
        # Добавление администраторов
        for admin_id in ADMIN_IDS:
            cursor.execute("INSERT IGNORE INTO admins (user_id) VALUES (%s)", (admin_id,))
        db.commit()
    except mysql.connector.Error as err:
        print("Ошибка при работе с MySQL:", err)
    finally:
        cursor.close()
        db.close()

# Темы
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

""" Админский блок """
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

# def get_admins():
#     db = get_db_connection()
#     cursor = db.cursor()
#     try:
#         cursor.execute("SELECT user_id FROM admins")
#         admins = cursor.fetchall()
#         return [admin[0] for admin in admins] 
#     finally:
#         cursor.close()
#         db.close()

def get_admins():
    # Считываем ID администраторов из .env
    env_admins = set(config.ADMIN_IDS)
    # Получаем список администраторов из базы данных
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
    # Объединяем оба списка
    return list(env_admins.union(db_admins))


""" Тикеры """

# Добавление тикера
def add_new_ticker(ticker_name, direction, entry_point, take_profit, stop_loss, current_rate, setup_image_path):
    entry_point = round(entry_point, 4)
    take_profit = round(take_profit, 4)
    stop_loss = round(stop_loss, 4)
    current_rate = round(current_rate, 4)

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
# Список всех тикеров
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

# Удаление тикера
def delete_ticker(ticker_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # First, fetch the path of the setup image for the ticker
        cursor.execute("SELECT setup_image_path FROM tickers WHERE id = %s", (ticker_id,))
        setup_image_path = cursor.fetchone()
        if setup_image_path and os.path.exists(setup_image_path[0]):
            os.remove(setup_image_path[0])  # Delete the file if it exists

        # Then, delete the ticker from the database
        cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error deleting ticker: {e}")
    finally:
        cursor.close()
        connection.close()

# Обновление тикера
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

# Ticker's monitoring
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

# Вход в сделкb
def confirm_entry(ticker_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE tickers SET entry_confirmed = TRUE WHERE id = %s", (ticker_id,))
        connection.commit()
    finally:
        cursor.close()
        connection.close()

# Активные сделки
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

# Отмена сделки (из списка активных)
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

# Детали сделки   
def get_trade_details(trade_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, ticker, entry_point, take_profit, stop_loss, current_rate, direction, active, setup_image_path
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
            'setup_image_path': trade[8]
        } if trade else None
    finally:
        cursor.close()
        connection.close()

# Архивация тикеров
# def archive_tickers():
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         # Выборка всех неактивных тикеров
#         cursor.execute("SELECT * FROM tickers WHERE active = 0")
#         tickers = cursor.fetchall()
#         logging.debug(f"Archiving tickers: {tickers}")  # Добавим логирование получаемых данных

#         for ticker in tickers:
#             try:
#                 id, ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, _, direction = ticker
#                 logging.debug(f"Ticker to archive: {ticker}")  # Просмотр каждого тикера перед обработкой

#                 # Определение статуса сделки
#                 status = "прибыль" if current_rate >= take_profit else "убыток"
#                 close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#                 # Вставка в архив
#                 cursor.execute("""
#                 INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#                 """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))

#                 # Удаление из основной таблицы
#                 cursor.execute("DELETE FROM tickers WHERE id = %s", (id,))
#             except ValueError as e:
#                 logging.error(f"Error processing ticker for archiving: {ticker}, Error: {e}")

#         connection.commit()
#     except mysql.connector.Error as e:
#         logging.error(f"Ошибка при архивации тикеров: {e}")
#     finally:
#         cursor.close()
#         connection.close()

def archive_tickers():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # Выборка всех неактивных тикеров
        cursor.execute("SELECT * FROM tickers WHERE active = 0")
        tickers = cursor.fetchall()
        logging.debug(f"Archiving tickers: {tickers}") 

        for ticker in tickers:
            # Убедитесь, что количество переменных соответствует количеству полей в запросе
            id, ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, active, direction, _ = ticker

            # Определение статуса сделки
            status = "прибыль" if current_rate >= take_profit else "убыток"
            close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Вставка в архив
            cursor.execute("""
            INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))

            # Удаление из основной таблицы
            cursor.execute("DELETE FROM tickers WHERE id = %s", (id,))

        connection.commit()
    except mysql.connector.Error as e:
        logging.error(f"Ошибка при архивации тикеров: {e}")
    finally:
        cursor.close()
        connection.close()

def archive_and_remove_ticker(ticker_id, current_rate, status):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # Получаем данные тикера для архивации
        cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
        ticker = cursor.fetchone()
        if ticker:
            ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker
            close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Вставка в архив
            cursor.execute("""
            INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
            # Удаление из таблицы tickers
            cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error archiving and deleting ticker: {e}")
    finally:
        cursor.close()
        connection.close()


# def archive_and_remove_ticker(ticker_id, current_rate, status):
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         # Получаем данные тикера для архивации
#         cursor.execute("SELECT ticker, entry_point, take_profit, stop_loss, setup_image_path, direction FROM tickers WHERE id = %s", (ticker_id,))
#         ticker = cursor.fetchone()
#         if ticker:
#             ticker_name, entry_point, take_profit, stop_loss, setup_image_path, direction = ticker
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             # Вставка в архив
#             cursor.execute("""
#             INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))
#             # Удаление из таблицы tickers
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (ticker_id,))
#         connection.commit()
#     except mysql.connector.Error as e:
#         print(f"Error archiving and deleting ticker: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# def archive_tickers():
#     connection = get_db_connection()
#     cursor = connection.cursor()
#     try:
#         # Выборка всех неактивных тикеров
#         cursor.execute("SELECT * FROM tickers WHERE active = 0")
#         tickers = cursor.fetchall()

#         for ticker in tickers:
#             id, ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, _, direction = ticker

#             # Определение статуса сделки
#             status = "прибыль" if current_rate >= take_profit else "убыток"
#             close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#             # Вставка в архив
#             cursor.execute("""
#             INSERT INTO archive (ticker, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (ticker_name, entry_point, take_profit, stop_loss, current_rate, setup_image_path, direction, close_date, status))

#             # Удаление из основной таблицы
#             cursor.execute("DELETE FROM tickers WHERE id = %s", (id,))

#         connection.commit()
#     except mysql.connector.Error as e:
#         print(f"Ошибка при архивации тикеров: {e}")
#     finally:
#         cursor.close()
#         connection.close()

# Удаление архивной сделки
def delete_archived_trade(trade_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # Получить путь к изображению для удаления файла, если он существует
        cursor.execute("SELECT setup_image_path FROM archive WHERE id = %s", (trade_id,))
        setup_image_path = cursor.fetchone()
        if setup_image_path and os.path.exists(setup_image_path[0]):
            os.remove(setup_image_path[0])

        # Удаление сделки из архива
        cursor.execute("DELETE FROM archive WHERE id = %s", (trade_id,))
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error deleting archived trade: {e}")
    finally:
        cursor.close()
        connection.close()

# Удаление всех сделок из архива
def delete_all_archived_trades():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # Удаление всех изображений перед очисткой архива
        cursor.execute("SELECT setup_image_path FROM archive")
        image_paths = cursor.fetchall()
        for path in image_paths:
            if path[0] and os.path.exists(path[0]):
                os.remove(path[0])

        # Удаление всех записей из архива
        cursor.execute("DELETE FROM archive")
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Error deleting all archived trades: {e}")
    finally:
        cursor.close()
        connection.close()

"""CHATS"""
# Получение всех чатов
def get_all_chats():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT chat_id FROM chats")
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

# Добавление чата
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
