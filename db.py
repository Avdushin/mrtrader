# db.py
import mysql.connector
from datetime import datetime
from config import DB_CONFIG, ADMIN_IDS,IMAGE_UPLOAD_PATH
import os

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
            active BOOLEAN,
            direction VARCHAR(10)
        )
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

def get_admins():
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT user_id FROM admins")
        admins = cursor.fetchall()
        return [admin[0] for admin in admins] 
    finally:
        cursor.close()
        db.close()

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