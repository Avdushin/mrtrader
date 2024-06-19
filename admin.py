import config

def is_admin(user_id):
    return user_id in config.ADMIN_IDS
