# commands.py
from telebot import types
from db import is_admin, add_admin, remove_admin, get_admins, confirm_entry
from tickers import *
from admin import is_admin
from ROI import calculate_roi
import mysql.connector

# Global variable to track selected trades
selected_trades = set()

def register_handlers(bot):
    @bot.message_handler(commands=['start', 'help'])
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        if is_admin(message.from_user.id):
            # Административная клавиатура
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("Архив сделок"), types.KeyboardButton("⚙️ Панель администратора"))
            bot.reply_to(message, "Привет, администратор! Выберите действие:", reply_markup=markup)
        else:
            # Клавиатура для обычных пользователей
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            # markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("ℹ️ Помощь"))
            markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("Архив сделок"), types.KeyboardButton("ℹ️ Помощь"))
            bot.reply_to(message, """Привет!
Я Mr. Trader - бот, который поможет торговать тебе и заработать мильоны тысяч зелёных бумажек!
Мои создатели просят меня мониторить различные токены, а я в свою очередь делюсь оперативной информацией по всем точкам входа с тобой!
Уда.чной торговли!""", reply_markup=markup)


    @bot.message_handler(func=lambda message: message.text == "📈 Тикеры")
    def ticker_handler(message):
        if is_admin(message.from_user.id):
            manage_tickers(bot, message)  # Полный доступ для администраторов
        else:
            manage_tickers(bot, message)  # Только просмотр списка тикеров для обычных пользователей


    @bot.message_handler(func=lambda message: message.text == "⚙️ Панель администратора")
    def admin_panel(message):
        # Это событие срабатывает, когда пользователь нажимает кнопку "Панель администратора"
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "У вас нет прав администратора.")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Добавить администратора", callback_data="add_admin"))
        markup.add(types.InlineKeyboardButton(text="Удалить администратора", callback_data="remove_admin"))
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


    @bot.callback_query_handler(func=lambda call: call.data == "add_admin")
    def prompt_new_admin(call):
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Отмена", callback_data="cancel_add_admin"))
        msg = bot.send_message(call.message.chat.id, "Введите ID нового администратора:", reply_markup=markup)
        bot.register_next_step_handler(msg, lambda message: process_add_admin(message, bot))

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_add_admin")
    def cancel_add_admin(call):
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Добавление нового администратора отменено.")

    @bot.callback_query_handler(func=lambda call: call.data == "remove_admin")
    def prompt_remove_admin(call):
        bot.answer_callback_query(call.id)
        admins = get_admins()
        if not admins:
            bot.send_message(call.message.chat.id, "Нет администраторов для удаления.")
            return
        markup = types.InlineKeyboardMarkup()
        for admin_id in admins:
            markup.add(types.InlineKeyboardButton(text=f"Удалить {admin_id}", callback_data=f"del_admin_{admin_id}"))
        bot.send_message(call.message.chat.id, "Выберите администратора для удаления:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_admin_"))
    def confirm_remove_admin(call):
        bot.answer_callback_query(call.id)
        admin_id = int(call.data.split("_")[2])
        remove_admin(admin_id)
        bot.send_message(call.message.chat.id, f"Администратор {admin_id} удален.")

    """ TICKERS """
    @bot.message_handler(func=lambda message: message.text == "📈 Тикеры")
    def ticker_handler(message):
        if is_admin(message.from_user.id):
            manage_tickers(bot, message)
        else:
            bot.send_message(message.chat.id, "У вас нет прав для управления тикерами.")

    # Добавление тикера
    @bot.callback_query_handler(func=lambda call: call.data == 'add_ticker')
    def handle_add_ticker(call):
        initiate_add_ticker(bot, call)
    
    # Выбор направления торговли
    @bot.callback_query_handler(func=lambda call: 'direction' in call.data)
    def handle_direction_selection(call):
        process_direction(bot, call)

#   # Выбор биржи для курса
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
    # Информация о тикерах
    @bot.message_handler(commands=['tickers'], func=lambda message: message.text == "Список тикеров")
    def handle_tickers_command(message):
        show_ticker_list(bot, message)


    # Удаление тикера
    @bot.callback_query_handler(func=lambda call: call.data == "delete_ticker")
    def handle_delete_ticker(call):
        delete_ticker(bot, call)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
    def handle_confirm_delete_ticker(call):
        confirm_delete_ticker(bot, call)

     # Отмена добавления тикера
    @bot.callback_query_handler(func=lambda call: call.data == "cancel_add_ticker")
    def cancel_add_ticker(call):
        bot.answer_callback_query(call.id, "Добавление тикера отменено.")
        bot.edit_message_text("Добавление тикера было отменено.", call.message.chat.id, call.message.message_id)

    # Отмена удаления тикера
    @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
    def handle_cancel_delete(bot, call):
        bot.answer_callback_query(call.id, "Удаление отменено.")
        bot.edit_message_text("Удаление тикера отменено.", call.message.chat.id, call.message.message_id)

    # Обновление тикеров
    # Обработчик для начала редактирования
    @bot.callback_query_handler(func=lambda call: call.data == "edit_ticker")
    def handle_edit_ticker(call):
        edit_ticker(bot, call)

    # Обработчик для выбора поля для редактирования
    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_") and not call.data.startswith("editfield_"))
    def handle_edit_selection(call):
        select_field_to_edit(bot, call)

    # Обработчик для ввода нового значения поля
    @bot.callback_query_handler(func=lambda call: call.data.startswith("editfield_"))
    def handle_field_edit(call):
        get_new_value(bot, call)
    
    # Отмена изменения тикера
    @bot.callback_query_handler(func=lambda call: call.data == "cancel_edit")
    def handle_cancel_edit(call):
        bot.answer_callback_query(call.id, "Редактирование отменено.")
        bot.send_message(call.message.chat.id, "Редактирование отменено. Возвращаемся в главное меню.")
        manage_tickers(bot, call.message)
    
    # Tickers monitoring
    @bot.message_handler(commands=['show_tickers'])
    def send_tickers_list(message):
        show_ticker_list(bot, message)

    @bot.message_handler(commands=['chat_id'])
    def print_chat_id(message):
        print("\n\nChat ID:\n\n", message.chat.id)
        bot.reply_to(message, f"Chat ID: {message.chat.id}")

    @bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
    def ticker_handler(message):
        if is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Дурик, ты и так всё знаешь =)")
        else:
            bot.send_message(message.chat.id, "Если у вас появились вопросы свяжитесь с автором бота: @Itdobro")
    
    # Вход в сделку
    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_entry_"))
    def confirm_entry_handler(call):
        ticker_id = int(call.data.split('_')[2])
        confirm_entry(ticker_id)
        bot.answer_callback_query(call.id, "Вход в сделку подтвержден.")
        bot.send_message(call.message.chat.id, "Вход в сделку подтвержден. Будут отправлены только уведомления о тейк-профите или стоп-лоссе.")

    # @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_entry_"))
    # def confirm_entry_handler(call):
    #     ticker_id = int(call.data.split('_')[2])
    #     db.confirm_entry(ticker_id)
    #     bot.answer_callback_query(call.id, "Вход в сделку подтвержден.")
    #     bot.send_message(call.message.chat.id, "Вход в сделку подтвержден. Будут отправлены только уведомления о тейк-профите или стоп-лоссе.")

    # @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_entry_"))
    # def confirm_entry(call):
    #     ticker_id = int(call.data.split('_')[2])
    #     db.confirm_entry(ticker_id)
    #     bot.answer_callback_query(call.id, "Вход в сделку подтвержден. Уведомления о приближении к точке входа больше не будут отправляться.")

    # Активные сделки
    @bot.callback_query_handler(func=lambda call: call.data == "active_trades")
    def show_active_trades(call):
        active_trades = db.get_active_trades()
        if not active_trades:
            bot.send_message(call.message.chat.id, "Нет активных сделок.")
            return

        markup = types.InlineKeyboardMarkup()
        for trade in active_trades:
            button_text = f"{trade['ticker']} - {trade['direction']}"
            callback_data = f"trade_info_{trade['id']}"
            markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

        bot.send_message(call.message.chat.id, "Активные сделки:", reply_markup=markup)

    # Детали активной сделки
    @bot.callback_query_handler(func=lambda call: call.data.startswith("trade_info_"))
    def trade_info(call):
        trade_id = int(call.data.split('_')[2])
        trade = db.get_trade_details(trade_id)
        if trade:
            if trade['setup_image_path'] and os.path.exists(trade['setup_image_path']):
                with open(trade['setup_image_path'], 'rb') as photo:
                    bot.send_photo(call.message.chat.id, photo)
            else:
                bot.send_message(call.message.chat.id, "Картинка сетапа не найдена.")

            info = (f"<b>Тикер:</b> {trade['ticker']}\n"
                    f"<b>Направление:</b> {trade['direction']}\n"
                    f"<b>Точка входа:</b> {trade['entry_point']}\n"
                    f"<b>Тейк-профит:</b> {trade['take_profit']}\n"
                    f"<b>Стоп-лосс:</b> {trade['stop_loss']}\n"
                    f"<b>Текущий курс:</b> {trade['current_rate']}\n"
                    f"<b>Статус:</b> {'Активна' if trade['active'] else 'Неактивна'}")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Выйти из сделки", callback_data=f"cancel_trade_{trade['id']}"))
            bot.send_message(call.message.chat.id, info, parse_mode='HTML', reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "Сделка не найдена.")

    # Отмена сделки (из списка активных)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_trade_"))
    def cancel_trade(call):
        trade_id = int(call.data.split('_')[2])
        db.cancel_trade(trade_id)
        bot.answer_callback_query(call.id, "Сделка отменена.")
        bot.edit_message_text("Сделка успешно отменена.", call.message.chat.id, call.message.message_id)

    """ АРХИВ СДЕЛОК """
    @bot.message_handler(func=lambda message: message.text == "Архив сделок")
    def handle_archive_button(message):
        show_archive_tickers_list(bot, message)

    @bot.callback_query_handler(func=lambda call: call.data == "show_archive")
    def show_archive(call):
        bot.answer_callback_query(call.id)
        archive_tickers_list(bot, call.message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("archive_"))
    def show_archive_details(call):
        parts = call.data.split('_')
        if len(parts) < 3 or not parts[2].isdigit():
            bot.send_message(call.message.chat.id, "Некорректные данные. Пожалуйста, повторите попытку.")
            return

        ticker_id = int(parts[2])
        connection = db.get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT * FROM archive WHERE id = %s", (ticker_id,))
            ticker = cursor.fetchone()
            if ticker:
                info = (
                    f"<b>Тикер:</b> {ticker[1]}\n"
                    f"<b>Точка входа:</b> {ticker[2]}\n"
                    f"<b>Тейк-профит:</b> {ticker[3]}\n"
                    f"<b>Стоп-лосс:</b> {ticker[4]}\n"
                    f"<b>Текущий курс:</b> {ticker[5]}\n"
                    f"<b>Дата закрытия:</b> {ticker[8].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"<b>Статус:</b> {ticker[9]}"
                )
                bot.send_message(call.message.chat.id, info, parse_mode='HTML')
                if ticker[6] and os.path.exists(ticker[6]):
                    with open(ticker[6], 'rb') as photo:
                        bot.send_photo(call.message.chat.id, photo)
            else:
                bot.send_message(call.message.chat.id, "Сделка не найдена.")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Ошибка: {e}")
        finally:
            cursor.close()
            connection.close()

    # Очистка архива
    @bot.callback_query_handler(func=lambda call: call.data == "clear_all_archive")
    def confirm_clear_all_archive(call):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Подтвердить", callback_data="confirm_clear_all"),
                types.InlineKeyboardButton("Отмена", callback_data="cancel_clear_all"))
        bot.send_message(call.message.chat.id, "Вы уверены, что хотите очистить архив сделок?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_clear_all")
    def clear_all_archive(call):
        db.delete_all_archived_trades()
        bot.answer_callback_query(call.id, "Архив сделок полностью очищен.")
        bot.edit_message_text("Все сделки из архива удалены.", call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_clear_all")
    def cancel_clear_all(call):
        bot.answer_callback_query(call.id, "Очистка архива отменена.")
        bot.edit_message_text("Очистка архива сделок отменена.", call.message.chat.id, call.message.message_id)

    # Удалить сделку из архива
    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_archive_"))
    def delete_selected_archived(call):
        trade_id = int(call.data.split('_')[2])
        db.delete_archived_trade(trade_id)
        bot.answer_callback_query(call.id, "Архивная сделка удалена.")
        bot.edit_message_text("Сделка успешно удалена из архива.", call.message.chat.id, call.message.message_id)

    # пункты архива
    @bot.callback_query_handler(func=lambda call: call.data == "show_archive_options")
    def show_archive_tickers_list(bot, message):
        connection = db.get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT id, ticker, status FROM archive")
            tickers = cursor.fetchall()
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("Очистить архив", callback_data="clear_all_archive"))
            markup.row(types.InlineKeyboardButton("Выборочное удаление сделок", callback_data="selective_delete_trades"))
            for id, ticker, status in tickers:
                markup.add(types.InlineKeyboardButton(f"{ticker} - {status}", callback_data=f"archive_select_{id}"))
            bot.send_message(message.chat.id, "Архив сделок:", reply_markup=markup)
        except mysql.connector.Error as e:
            bot.send_message(message.chat.id, f"Ошибка при получении данных: {e}")
        finally:
            cursor.close()
            connection.close()

    # Выбор сделок для удаления из архива
    @bot.callback_query_handler(func=lambda call: call.data.startswith("archive_select_"))
    def select_trade_for_deletion(call):
        trade_id = call.data.split('_')[2]
        if trade_id in selected_trades:
            selected_trades.remove(trade_id)
            bot.answer_callback_query(call.id, "Сделка удалена из списка на удаление.")
        else:
            selected_trades.add(trade_id)
            bot.answer_callback_query(call.id, "Сделка добавлена в список на удаление.")
        update_selected_trades_message(bot, call.message.chat.id)

    def update_selected_trades_message(bot, chat_id):
        if selected_trades:
            selected_info = "Выбранные сделки для удаления: " + ', '.join(selected_trades)
        else:
            selected_info = "Нет выбранных сделок."
        bot.send_message(chat_id, selected_info)

    @bot.callback_query_handler(func=lambda call: call.data == "selective_delete_trades")
    def show_archive_tickers_list_for_deletion(call):
        connection = db.get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT id, ticker, status FROM archive")
            tickers = cursor.fetchall()
            if not tickers:
                bot.send_message(call.message.chat.id, "Архив пуст.")
                return
            markup = types.InlineKeyboardMarkup()
            for id, ticker, status in tickers:
                # Ensure deletion functionality is distinct
                markup.add(types.InlineKeyboardButton(f"Удалить {ticker} - {status}", callback_data=f"delete_archive_{id}"))
            bot.send_message(call.message.chat.id, "Выберите сделки для удаления:", reply_markup=markup)
        except mysql.connector.Error as e:
            bot.send_message(call.message.chat.id, f"Ошибка при получении данных: {e}")
        finally:
            cursor.close()
            connection.close()

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_delete_selected")
    def delete_selected_trades(call):
        for trade_id in selected_trades:
            db.delete_archived_trade(trade_id)
        selected_trades.clear()  # Clear after deletion
        bot.answer_callback_query(call.id, "Выбранные сделки удалены.")
        bot.edit_message_text("Выбранные сделки успешно удалены из архива.", call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete_selected")
    def cancel_delete_selected(call):
        selected_trades.clear()
        bot.answer_callback_query(call.id, "Удаление выбранных сделок отменено.")
        bot.edit_message_text("Удаление выбранных сделок отменено.", call.message.chat.id, call.message.message_id)

### =============================================================================

def process_add_admin(message, bot):
    try:
        user_id = int(message.text)
        add_admin(user_id)
        bot.reply_to(message, f"Пользователь {user_id} добавлен в администраторы.")
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите корректный числовой ID.")


def process_remove_admin(message, bot):
    try:
        user_id = int(message.text)
        remove_admin(user_id)
        bot.reply_to(message, f"Пользователь {user_id} удален из администраторов.")
    except ValueError:
        bot.reply_to(message, "Пожалуйста, выберите другого пользователя - этот бог")
