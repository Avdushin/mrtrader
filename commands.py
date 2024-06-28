# commands.py
from telebot import types
from db import is_admin, add_admin, remove_admin, get_admins, confirm_entry
from tickers import *
from admin import is_admin, is_god
from ROI import calculate_roi
from config import PREFERRED_CHAT_ID, ALARM_CHAT_ID, ALARM_THEME_ID
import mysql.connector

# Global variable to track selected trades
selected_trades = set()

def register_handlers(bot):
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        chat_id = message.chat.id
        print("\n\nReceived chat ID:\n\n", chat_id)
        
        if chat_id == ALARM_CHAT_ID:
            if is_god(message.from_user.id):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("Архив сделок"))
                markup.row(types.KeyboardButton("⚙️ Панель администратора"), types.KeyboardButton("🧙🏻‍♂️ Асгард"))
                bot.send_message(chat_id, "Привет, администратор! Выберите действие", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
            elif is_admin(message.from_user.id):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("Архив сделок"))
                markup.row(types.KeyboardButton("⚙️ Панель администратора"))
                bot.send_message(chat_id, "Привет, администратор! Выберите действие:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("Архив сделок"), types.KeyboardButton("ℹ️ Помощь"))
                bot.send_message(chat_id, """Привет!
Я Mr. Trader - бот, который поможет торговать тебе и заработать мильоны тысяч зелёных бумажек!
Мои создатели просят меня мониторить различные токены, а я в свою очередь делюсь оперативной информацией по всем точкам входа с тобой!
Удачной торговли!""", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

    @bot.message_handler(commands=['get_threads'])
    def get_threads(message):
        chat_id = ALARM_CHAT_ID
        threads = get_threads_from_db_or_api(chat_id)
        response = "Список тем:\n"
        for thread in threads:
            response += f"Название: {thread['name']} - ID: {thread['thread_id']}\n"
        bot.send_message(ALARM_CHAT_ID, response, message_thread_id=ALARM_THEME_ID)

    def get_threads_from_db_or_api(chat_id):
        return [
            {'name': 'General', 'thread_id': 1},
            {'name': 'Alarm', 'thread_id': 3231}
        ]

    @bot.message_handler(func=lambda message: message.text == "📈 Тикеры")
    def ticker_handler(message):
        if is_admin(message.from_user.id):
            # Полный доступ для администраторов
            manage_tickers(bot, message)
        else:
            # Только просмотр списка тикеров для обычных пользователей
            manage_tickers(bot, message)

    @bot.message_handler(func=lambda message: message.text == "🧙🏻‍♂️ Асгард")
    def god_panel(message):
        if not is_god(message.from_user.id):
            bot.send_message(ALARM_CHAT_ID, "Привет, администратор! Выберите действие", message_thread_id=ALARM_THEME_ID)
            return
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("Архив сделок"))
        markup.row(types.KeyboardButton("⚙️ Панель администратора"), types.KeyboardButton("📨Чаты"))
        bot.send_message(ALARM_CHAT_ID, "Добро пожаловать в Асгард! Созидай на здоровье =):", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

    @bot.message_handler(commands=['set_theme'])
    def set_theme(message):
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(ALARM_CHAT_ID, "Пожалуйста, укажите тему.", message_thread_id=ALARM_THEME_ID)
            return
        theme = parts[1]
        db.set_user_theme(message.from_user.id, theme)
        bot.send_message(ALARM_CHAT_ID, f"Тема изменена на: {theme}", message_thread_id=ALARM_THEME_ID)

    @bot.message_handler(func=lambda message: message.text == "📨Чаты")
    def chat_management(message):
        if not is_god(message.from_user.id):
            bot.send_message(ALARM_CHAT_ID, "У вас нет прав для управления чатами.", message_thread_id=ALARM_THEME_ID)
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Добавить чат", callback_data="add_chat"),
                   types.InlineKeyboardButton("Удалить чат", callback_data="remove_chat"))
        bot.send_message(ALARM_CHAT_ID, "Управление чатами:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "add_chat")
    def add_chat(call):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_chat"))
        msg = bot.send_message(ALARM_CHAT_ID, "Введите ID чата для добавления:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
        bot.register_next_step_handler(msg, process_add_chat)

    def process_add_chat(message):
        chat_id = message.text.strip()
        if chat_id:
            db.add_chat_to_db(chat_id)
            bot.send_message(ALARM_CHAT_ID, f"Чат {chat_id} успешно добавлен.", message_thread_id=ALARM_THEME_ID)
        else:
            bot.send_message(ALARM_CHAT_ID, "Введите корректный ID чата.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_add_chat")
    def cancel_add_chat(call):
        bot.answer_callback_query(call.id, "Добавление чата отменено.")
        bot.edit_message_text("Добавление чата было отменено.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "remove_chat")
    def prompt_remove_chat(call):
        bot.answer_callback_query(call.id)
        chat_ids = db.get_all_chats()
        admin_chats = set(config.ADMIN_CHAT_IDS)
        all_chats = set(chat_ids).union(admin_chats)

        if not all_chats:
            bot.send_message(ALARM_CHAT_ID, "Нет чатов для удаления.", message_thread_id=ALARM_THEME_ID)
            return

        markup = types.InlineKeyboardMarkup()
        for chat_id in all_chats:
            markup.add(types.InlineKeyboardButton(text=f"Удалить {chat_id}", callback_data=f"del_chat_{chat_id}"))
        bot.send_message(ALARM_CHAT_ID, "Выберите чат для удаления:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_chat_"))
    def confirm_remove_chat(call):
        chat_id = int(call.data.split("_")[2])
        db.remove_chat_from_db(chat_id)
        if chat_id in config.ADMIN_CHAT_IDS:
            config.ADMIN_CHAT_IDS.remove(chat_id)
        bot.answer_callback_query(call.id, "Чат удален.")
        bot.send_message(ALARM_CHAT_ID, f"Чат {chat_id} успешно удален.", message_thread_id=ALARM_THEME_ID)

    @bot.message_handler(func=lambda message: message.text == "⚙️ Панель администратора")
    def admin_panel(message):
        if not is_admin(message.from_user.id):
            bot.send_message(ALARM_CHAT_ID, "У вас нет прав администратора.", message_thread_id=ALARM_THEME_ID)
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Добавить администратора", callback_data="add_admin"))
        markup.add(types.InlineKeyboardButton(text="Удалить администратора", callback_data="remove_admin"))
        bot.send_message(ALARM_CHAT_ID, "Выберите действие:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "add_admin")
    def prompt_new_admin(call):
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Отмена", callback_data="cancel_add_admin"))
        msg = bot.send_message(ALARM_CHAT_ID, "Введите ID нового администратора:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
        bot.register_next_step_handler(msg, lambda message: process_add_admin(message, bot))

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_add_admin")
    def cancel_add_admin(call):
        bot.answer_callback_query(call.id)
        bot.send_message(ALARM_CHAT_ID, "Добавление нового администратора отменено.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "remove_admin")
    def prompt_remove_admin(call):
        bot.answer_callback_query(call.id)
        admins = get_admins()
        if not admins:
            bot.send_message(ALARM_CHAT_ID, "Нет администраторов для удаления.", message_thread_id=ALARM_THEME_ID)
            return
        markup = types.InlineKeyboardMarkup()
        for admin_id in admins:
            markup.add(types.InlineKeyboardButton(text=f"Удалить {admin_id}", callback_data=f"del_admin_{admin_id}"))
        bot.send_message(ALARM_CHAT_ID, "Выберите администратора для удаления:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_admin_"))
    def confirm_remove_admin(call):
        bot.answer_callback_query(call.id)
        admin_id = int(call.data.split("_")[2])
        remove_admin(admin_id)
        bot.send_message(ALARM_CHAT_ID, f"Администратор {admin_id} удален.", message_thread_id=ALARM_THEME_ID)

    @bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
    def help_handler(message):
        if is_admin(message.from_user.id):
            bot.send_message(ALARM_CHAT_ID, "Дурик, ты и так всё знаешь =)", message_thread_id=ALARM_THEME_ID)
        else:
            bot.send_message(ALARM_CHAT_ID, "Если у вас появились вопросы, свяжитесь с автором бота: @Itdobro", message_thread_id=ALARM_THEME_ID)

    @bot.message_handler(func=lambda message: message.text == "Архив сделок")
    def show_archive(message):
        archive_tickers_list(bot, message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("archive_"))
    def show_archived_trade(call):
        trade_id = int(call.data.split('_')[1])
        connection = db.get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT * FROM archive WHERE id = %s", (trade_id,))
            trade = cursor.fetchone()
            if trade:
                info = (
                    f"<b>Тикер:</b> <code>{trade[1]}</code>\n"
                    f"<b>Точка входа:</b> <code>{trade[2]}</code>\n"
                    f"<b>Тейк-профит:</b> <code>{trade[3]}</code>\n"
                    f"<b>Стоп-лосс:</b> <code>{trade[4]}</code>\n"
                    f"<b>Текущий курс:</b> <code>{trade[5]}</code>\n"
                    f"<b>Дата закрытия:</b> <code>{trade[8].strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"<b>Статус:</b> <code>{trade[9]}</code>"
                )
                bot.send_message(config.ALARM_CHAT_ID, info, parse_mode="HTML", message_thread_id=config.ALARM_THEME_ID)
                if trade[6] and os.path.exists(trade[6]):
                    with open(trade[6], 'rb') as photo:
                        bot.send_photo(config.ALARM_CHAT_ID, photo, message_thread_id=config.ALARM_THEME_ID)
            else:
                bot.send_message(config.ALARM_CHAT_ID, "Сделка не найдена.", message_thread_id=config.ALARM_THEME_ID)
        except Exception as e:
            bot.send_message(config.ALARM_CHAT_ID, f"Ошибка при получении данных: {str(e)}", message_thread_id=config.ALARM_THEME_ID)
        finally:
            cursor.close()
            connection.close()


    @bot.callback_query_handler(func=lambda call: call.data == "clear_all_archive")
    def confirm_clear_all_archive(call):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Подтвердить", callback_data="confirm_clear_all"),
                   types.InlineKeyboardButton("Отмена", callback_data="cancel_clear_all"))
        bot.send_message(ALARM_CHAT_ID, "Вы уверены, что хотите очистить архив сделок?", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

    # @bot.callback_query_handler(func=lambda call: call.data == "confirm_clear_all")
    # def clear_all_archive(call):
    #     db.delete_all_archived_trades()
    #     bot.answer_callback_query(call.id, "Архив сделок полностью очищен.")
    #     bot.edit_message_text("Все сделки из архива удалены.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=config.ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_clear_all")
    def clear_all_archive(call):
        db.delete_all_archived_trades()
        bot.answer_callback_query(call.id, "Архив сделок полностью очищен.")
        bot.send_message(ALARM_CHAT_ID, "Все сделки из архива удалены.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_clear_all")
    def cancel_clear_all(call):
        bot.answer_callback_query(call.id, "Очистка архива отменена.")
        # Удаляем старое сообщение
        bot.delete_message(ALARM_CHAT_ID, call.message.message_id)
        # Отправляем новое сообщение
        bot.send_message(ALARM_CHAT_ID, "Очистка архива сделок отменена.", message_thread_id=ALARM_THEME_ID)

    # @bot.callback_query_handler(func=lambda call: call.data == "cancel_clear_all")
    # def cancel_clear_all(call):
    #     bot.answer_callback_query(call.id, "Очистка архива отменена.")
    #     bot.edit_message_text("Очистка архива сделок отменена.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=config.ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_clear_all")
    def clear_all_archive(call):
        db.delete_all_archived_trades()
        bot.answer_callback_query(call.id, "Архив сделок полностью очищен.")
        # Удаляем старое сообщение
        bot.delete_message(ALARM_CHAT_ID, call.message.message_id)
        # Отправляем новое сообщение
        bot.send_message(ALARM_CHAT_ID, "Все сделки из архива удалены.", message_thread_id=ALARM_THEME_ID)

    # @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_archive_"))
    # def delete_selected_archived(call):
    #     trade_id = int(call.data.split('_')[2])
    #     db.delete_archived_trade(trade_id)

    #     bot.edit_message_text("Сделка успешно удалена из архива.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=config.ALARM_THEME_ID)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_archive_"))
    def delete_selected_archived(call):
        trade_id = int(call.data.split('_')[2])
        db.delete_archived_trade(trade_id)
        bot.answer_callback_query(call.id, "Архивная сделка удалена.")
        # Удаляем старое сообщение
        bot.delete_message(ALARM_CHAT_ID, call.message.message_id)
        # Отправляем новое сообщение
        bot.send_message(ALARM_CHAT_ID, "Сделка успешно удалена из архива.", message_thread_id=ALARM_THEME_ID)   

    def update_selected_trades_message(bot, chat_id):
        if selected_trades:
            selected_info = "Выбранные сделки для удаления: " + ', '.join(selected_trades)
        else:
            selected_info = "Нет выбранных сделок."
        bot.send_message(chat_id, selected_info, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "selective_delete_trades")
    def show_archive_tickers_list_for_deletion(call):
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
                markup.add(types.InlineKeyboardButton(f"Удалить {ticker} - {status}", callback_data=f"delete_archive_{id}"))
            bot.send_message(ALARM_CHAT_ID, "Выберите сделки для удаления:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
        except mysql.connector.Error as e:
            bot.send_message(ALARM_CHAT_ID, f"Ошибка при получении данных: {e}", message_thread_id=ALARM_THEME_ID)
        finally:
            cursor.close()
            connection.close()

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_delete_selected")
    def delete_selected_trades(call):
        for trade_id in selected_trades:
            db.delete_archived_trade(trade_id)
        selected_trades.clear()
        bot.answer_callback_query(call.id, "Выбранные сделки удалены.")
        bot.edit_message_text("Выбранные сделки успешно удалены из архива.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=ALARM_THEME_ID)

    # @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete_selected")
    # def cancel_delete_selected(call):
    #     selected_trades.clear()
    #     bot.answer_callback_query(call.id, "Удаление выбранных сделок отменено.")
    #     bot.edit_message_text("Удаление выбранных сделок отменено.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete_selected")
    def cancel_delete_selected(call):
        selected_trades.clear()
        bot.answer_callback_query(call.id, "Удаление выбранных сделок отменено.")
        # Удаляем старое сообщение
        bot.delete_message(ALARM_CHAT_ID, call.message.message_id)
        # Отправляем новое сообщение
        bot.send_message(ALARM_CHAT_ID, "Удаление выбранных сделок отменено.", message_thread_id=ALARM_THEME_ID)

    """ TICKERS """
    @bot.message_handler(func=lambda message: message.text == "📈 Тикеры")
    def ticker_handler(message):
        if is_admin(message.from_user.id):
            manage_tickers(bot, message)
        else:
            bot.send_message(message.chat.id, "У вас нет прав для управления тикерами.", message_thread_id=ALARM_THEME_ID)

    # Добавление тикера
    @bot.callback_query_handler(func=lambda call: call.data == 'add_ticker')
    def handle_add_ticker(call):
        initiate_add_ticker(bot, call)
    
    # Выбор направления торговли
    @bot.callback_query_handler(func=lambda call: 'direction' in call.data)
    def handle_direction_selection(call):
        process_direction(bot, call)

    # Выбор биржи для курса
    @bot.callback_query_handler(func=lambda call: 'exchange' in call.data)
    def handle_exchange_selection_h(call):
        handle_exchange_selection(bot, call)
    
    @bot.callback_query_handler(func=lambda call: call.data == "show_tickers")
    def handle_show_tickers(call):
        show_ticker_list(bot, call.message)

    # Получение тикеров
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ticker_"))
    def handle_ticker_selection(call):
        show_ticker_info(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data == "delete_ticker")
    def handle_delete_ticker(call):
        delete_ticker(bot, call)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
    def handle_confirm_delete_ticker(call):
        confirm_delete_ticker(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_add_ticker")
    def cancel_add_ticker(call):
        bot.answer_callback_query(call.id, "Добавление тикера отменено.")
        bot.edit_message_text("Добавление тикера было отменено.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
    def handle_cancel_delete(call):
        bot.answer_callback_query(call.id, "Удаление отменено.")
        bot.edit_message_text("Удаление тикера отменено.", ALARM_CHAT_ID, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "edit_ticker")
    def handle_edit_ticker(call):
        edit_ticker(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_") and not call.data.startswith("editfield_"))
    def handle_edit_selection(call):
        select_field_to_edit(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("editfield_"))
    def handle_field_edit(call):
        get_new_value(bot, call)
    
    @bot.callback_query_handler(func=lambda call: call.data == "cancel_edit")
    def handle_cancel_edit(call):
        bot.answer_callback_query(call.id, "Редактирование отменено.")
        bot.send_message(ALARM_CHAT_ID, "Редактирование отменено. Возвращаемся в главное меню.", message_thread_id=ALARM_THEME_ID)
        manage_tickers(bot, call.message)
    
    @bot.message_handler(commands=['show_tickers'])
    def send_tickers_list(message):
        show_ticker_list(bot, message)

    @bot.message_handler(commands=['chat_id'])
    def print_chat_id(message):
        print("\n\nChat ID:\n\n", message.chat.id)
        bot.reply_to(message, f"Chat ID: {message.chat.id}")

    # @bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
    # def help_handler(message):
    #     if is_admin(message.from_user.id):
    #         bot.send_message(message.chat.id, "Дурик, ты и так всё знаешь =)", message_thread_id=ALARM_THEME_ID)
    #     else:
    #         bot.send_message(message.chat.id, "Если у вас появились вопросы свяжитесь с автором бота: @Itdobro", message_thread_id=ALARM_THEME_ID)
    
    # Вход в сделку
    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_entry_"))
    def confirm_entry_handler(call):
        ticker_id = int(call.data.split('_')[2])
        confirm_entry(ticker_id)
        bot.answer_callback_query(call.id, "Вход в сделку подтвержден.")
        bot.send_message(ALARM_CHAT_ID, "Вход в сделку подтвержден. Будут отправлены только уведомления о тейк-профите или стоп-лоссе.", message_thread_id=ALARM_THEME_ID)

    # Активные сделки
    @bot.callback_query_handler(func=lambda call: call.data == "active_trades")
    def show_active_trades(call):
        active_trades = db.get_active_trades()
        if not active_trades:
            bot.send_message(ALARM_CHAT_ID, "Нет активных сделок.", message_thread_id=ALARM_THEME_ID)
            return

        markup = types.InlineKeyboardMarkup()
        for trade in active_trades:
            button_text = f"{trade['ticker']} - {trade['direction']}"
            callback_data = f"trade_info_{trade['id']}"
            markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

        bot.send_message(ALARM_CHAT_ID, "Активные сделки:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

    # Детали активной сделки
    @bot.callback_query_handler(func=lambda call: call.data.startswith("trade_info_"))
    def trade_info(call):
        trade_id = int(call.data.split('_')[2])
        trade = db.get_trade_details(trade_id)
        if trade:
            if trade['setup_image_path'] and os.path.exists(trade['setup_image_path']):
                with open(trade['setup_image_path'], 'rb') as photo:
                    bot.send_photo(ALARM_CHAT_ID, photo, message_thread_id=ALARM_THEME_ID)
            else:
                bot.send_message(ALARM_CHAT_ID, "Картинка сетапа не найдена.", message_thread_id=ALARM_THEME_ID)

            info = (f"<b>Тикер:</b> {trade['ticker']}\n"
                    f"<b>Направление:</b> {trade['direction']}\n"
                    f"<b>Точка входа:</b> {trade['entry_point']}\n"
                    f"<b>Тейк-профит:</b> {trade['take_profit']}\n"
                    f"<b>Стоп-лосс:</b> {trade['stop_loss']}\n"
                    f"<b>Текущий курс:</b> {trade['current_rate']}\n"
                    f"<b>Статус:</b> {'Активна' if trade['active'] else 'Неактивна'}")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Выйти из сделки", callback_data=f"cancel_trade_{trade['id']}"))
            bot.send_message(ALARM_CHAT_ID, info, parse_mode='HTML', reply_markup=markup, message_thread_id=ALARM_THEME_ID)
        else:
            bot.send_message(ALARM_CHAT_ID, "Сделка не найдена.", message_thread_id=ALARM_THEME_ID)

    # Отмена сделки (из списка активных)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_trade_"))
    def cancel_trade(call):
        trade_id = int(call.data.split('_')[2])
        db.cancel_trade(trade_id)
        bot.answer_callback_query(call.id, "Сделка отменена.")
        bot.edit_message_text("Сделка успешно отменена.", ALARM_CHAT_ID, call.message.message_id, message_thread_id=ALARM_THEME_ID)

    def process_add_admin(message, bot):
        try:
            user_id = int(message.text)
            add_admin(user_id)
            bot.send_message(ALARM_CHAT_ID, f"Пользователь {user_id} добавлен в администраторы.", message_thread_id=ALARM_THEME_ID)
        except ValueError:
            bot.send_message(ALARM_CHAT_ID, "Пожалуйста, введите корректный числовой ID.", message_thread_id=ALARM_THEME_ID)

    def process_remove_admin(message, bot):
        try:
            user_id = int(message.text)
            remove_admin(user_id)
            bot.send_message(ALARM_CHAT_ID, f"Пользователь {user_id} удален из администраторов.", message_thread_id=ALARM_THEME_ID)
        except ValueError:
            bot.send_message(ALARM_CHAT_ID, "Пожалуйста, выберите другого пользователя - этот бог", message_thread_id=ALARM_THEME_ID)
