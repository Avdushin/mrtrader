import config
from db import get_db_connection

def is_admin(user_id):
    # Проверяем, есть ли пользователь в списке админов, загруженных из .env
    if user_id in config.ADMIN_IDS:
        return True
    # Если не найден, проверяем в базе данных
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM admins WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()[0]
            return result > 0
    finally:
        if connection:
            connection.close()
    return False

def is_god(user_id):
    return user_id in config.GODS

# import config

# def is_admin(user_id):
#     return user_id in config.ADMIN_IDS
