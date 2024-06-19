# commands.py
from telebot import types
from db import is_admin, add_admin, remove_admin, get_admins
from tickers import *
from admin import is_admin
from ROI import calculate_roi

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
        ticker_id = int(call.data.split('_')[1])
        connection = db.get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT * FROM archive WHERE id = %s", (ticker_id,))
            ticker = cursor.fetchone()
            if ticker:
                info = (
                    f"<b>Тикер:</b> #{ticker[1]}\n"
                    f"<b>Результаты сделки (ROI):</b> <code>{calculate_roi(ticker[2], ticker[3], ticker[4], ticker[5])}%</code>\n"
                    f"<b>Направление сделки:</b> <code>{ticker[7]}</code>\n"
                    f"<b>Точка входа:</b> <code>{ticker[2]}</code>\n"
                    f"<b>Тейк-профит:</b> <code>{ticker[3]}</code>\n"
                    f"<b>Стоп-лосс:</b> <code>{ticker[4]}</code>\n"
                    f"<b>Текущий курс:</b> <code>{ticker[5]}</code>\n"
                    f"<b>Дата закрытия:</b> <code>{ticker[8].strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"<b>Статус сделки:</b> <code>{ticker[9]}</code>"
                )
                bot.send_message(call.message.chat.id, info, parse_mode='HTML')
                if ticker[6] and os.path.exists(ticker[6]):
                    bot.send_photo(call.message.chat.id, open(ticker[6], 'rb'))
            else:
                bot.send_message(call.message.chat.id, "Сделка не найдена.")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Ошибка: {e}")
        finally:
            cursor.close()
            connection.close()

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
