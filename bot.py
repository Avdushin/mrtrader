# bot.py
import telebot
import threading
from config import TOKEN
from tickers import start_monitoring
import commands
import db
import backups

bot = telebot.TeleBot(TOKEN)

def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    db.setup_database()
    commands.register_handlers(bot)
    threading.Thread(target=start_monitoring, args=(bot,)).start()
    backups.start_backup_scheduler()
    run_bot()

# import telebot
# import threading
# from config import TOKEN
# from tickers import start_monitoring
# import commands
# import db
# import backups

# bot = telebot.TeleBot(TOKEN)

# def run_bot():
#     bot.polling(none_stop=True)

# if __name__ == "__main__":
#     db.setup_database()
#     commands.register_handlers(bot)
#     threading.Thread(target=start_monitoring, args=(bot,)).start()
#     backups.start_backup_scheduler()
#     run_bot()
