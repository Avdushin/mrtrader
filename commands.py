# commands.py
from telebot import types
from db import is_admin, add_admin, remove_admin, get_admins
from tickers import *

def register_handlers(bot):
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        if is_admin(message.from_user.id):
            # Показываем административную клавиатуру
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("⚙️ Панель администратора"))
            bot.reply_to(message, "Привет, администратор! Выберите действие:", reply_markup=markup)
        else:
            simple_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            simple_markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("ℹ️ Помощь"))
            bot.reply_to(message, """Привет!
Я Mr. Trader - бот, который поможет торговать тебе и заработать мильоны тысяч зелёных бумажек!
Мои создатели просят меня мониторить различные токены, а я в свою очередь делюсь оперативной информацией по всем точкам входа с тобой!
Уда.чной торговли!""", reply_markup=simple_markup)

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

    # Отмена удаления тикера
    @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
    def handle_cancel_delete(bot, call):
        bot.answer_callback_query(call.id, "Удаление отменено.")
        bot.edit_message_text("Удаление тикера отменено.", call.message.chat.id, call.message.message_id)

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
        user_id = int(message.text)  # Предполагаем, что ввод корректен
        remove_admin(user_id)
        bot.reply_to(message, f"Пользователь {user_id} удален из администраторов.")
    except ValueError:
        bot.reply_to(message, "Пожалуйста, выберите другого пользователя - этот бог")
