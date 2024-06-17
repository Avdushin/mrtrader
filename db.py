# db.py
import mysql.connector
from config import DB_CONFIG, ADMIN_IDS

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
            ticker VARCHAR(10),
            entry_point FLOAT,
            take_profit FLOAT,
            stop_loss FLOAT,
            current_rate FLOAT,
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

