# backups.py
import os
import shutil
import platform
import zipfile
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import config
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определение пути к mysqldump в зависимости от ОС
def get_mysqldump_path():
    if platform.system() == "Windows":
        return r'"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"'
    return "mysqldump"

# Функция для резервного копирования базы данных
def backup_database():
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    backup_file = os.path.join(backup_dir, f'db_backup_{datetime.now().strftime("%Y%m%d%H%M%S")}.sql')
    mysqldump_path = get_mysqldump_path()
    dump_cmd = f"{mysqldump_path} -h {config.DB_CONFIG['host']} -u {config.DB_CONFIG['user']} -p{config.DB_CONFIG['password']} {config.DB_CONFIG['database']} > {backup_file}"
    result = os.system(dump_cmd)
    
    if result == 0:
        logger.info(f"Database backup created: {backup_file}")
    else:
        logger.error("Database backup failed!")

# Функция для резервного копирования локальных файлов
def backup_files():
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    setup_images_dir = 'setups'
    if os.path.exists(setup_images_dir):
        dest_dir = os.path.join(backup_dir, f'setup_images_backup_{datetime.now().strftime("%Y%m%d%H%M%S")}')
        shutil.copytree(setup_images_dir, dest_dir)
        logger.info(f"Setup images backup created: {dest_dir}")
    else:
        logger.warning(f"Setup images directory '{setup_images_dir}' does not exist.")

# Функция для архивирования старых бэкапов
def archive_old_backups():
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    now = datetime.now().strftime("%Y%m%d%H%M%S")
    zip_filename = os.path.join(backup_dir, f'backup_archive_{now}.zip')
    
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                if not file.endswith('.zip'):
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, backup_dir))
                    os.remove(file_path)
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                shutil.rmtree(dir_path)
    
    logger.info(f"Old backups archived and removed: {zip_filename}")

# Основная функция для резервного копирования базы данных и локальных файлов
def backup_all():
    logger.info("Starting full backup...")
    archive_old_backups()
    backup_database()
    backup_files()
    logger.info("Full backup completed.")

# Функция для запуска планировщика
def start_backup_scheduler():
    timezone = pytz.timezone('Europe/Moscow')
    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(backup_all, 'interval', hours=8)
    scheduler.start()
    logger.info("Backup scheduler started.")
    # Запуск первого бэкапа немедленно для проверки
    backup_all()

if __name__ == '__main__':
    start_backup_scheduler()
