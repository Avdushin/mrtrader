# commands.py
from telebot import types
from db import is_admin, add_admin, remove_admin, get_admins, add_new_ticker
# import tickers
from tickers import *
# from tickers import manage_tickers, initiate_add_ticker, handle_action

user_state = {}


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

    @bot.message_handler(func=lambda message: message.text == "📈 Тикеры")
    def ticker_handler(message):
        if is_admin(message.from_user.id):
            manage_tickers(bot, message)  # Указываем модуль перед функцией
        else:
            bot.send_message(message.chat.id, "У вас нет прав для управления тикерами.")

    @bot.callback_query_handler(func=lambda call: call.data == 'add_ticker')
    def handle_add_ticker(call):
        initiate_add_ticker(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('direction_'))
    def handle_direction_selection(call):
        # Этот обработчик корректно обрабатывает callback_query
        direction = call.data.split('_')[1]  # Получаем направление (LONG или SHORT)
        user_state[call.message.chat.id]['direction'] = direction  # Сохраняем выбор в состоянии пользователя
        bot.answer_callback_query(call.id, "Направление выбрано: " + direction)
        bot.send_message(call.message.chat.id, "Введите стоп-лосс:")  # Переходим к следующему шагу
    
    def prompt_for_direction(message):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Long", callback_data="direction_LONG"),
                types.InlineKeyboardButton("Short", callback_data="direction_SHORT"))
        bot.send_message(message.chat.id, "Выберите направление сделки:", reply_markup=markup)

    # @bot.callback_query_handler(func=lambda call: call.data.startswith('direction_'))
    # def handle_direction_selection(call):
    #     direction = call.data.split('_')[1]  # direction_long или direction_short
    #     user_state[call.message.chat.id]['direction'] = direction.upper()  # Сохраняем как 'LONG' или 'SHORT'
    #     bot.answer_callback_query(call.id, "Направление выбрано: " + direction.upper())


    # Обработчик для выбора биржи
    # @bot.callback_query_handler(func=lambda call: call.data.startswith('exchange_'))
    # def exchange_callback(call):
    #     handle_exchange_selection(bot, call)
    # Обработчик для выбора биржи
    @bot.callback_query_handler(func=lambda call: call.data.startswith('exchange_'))
    def exchange_callback(call):
        handle_exchange_selection(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('change_exchange_'))
    def change_exchange_callback(call):
        # Ошибка была здесь: не передавался параметр 'call' в функцию.
        _, ticker_name = call.data.split('_')[1:]  # исправленный split, если 'change_exchange_' является началом строки
        ask_for_exchange(bot, call.message, ticker_name)

    # Обработчик для пропуска загрузки изображения
    @bot.callback_query_handler(func=lambda call: call.data.startswith('skip_setup'))
    def handle_skip_setup(call):
        parts = call.data.split('_')
        if len(parts) >= 4:
            # Извлекаем ticker_name и exchange, и объединяем оставшиеся части обратно в current_rate
            ticker_name = parts[2]
            exchange = parts[3]
            current_rate = '_'.join(parts[4:])  # Объединяем все части, содержащие цену
            bot.answer_callback_query(call.id, "Шаг пропущен.")
            bot.send_message(call.message.chat.id, f"Вы пропустили этап ввода изображения сетапа. Пожалуйста, введите точку входа для {ticker_name} на бирже {exchange}.")
            # Сохраняем состояние для использования в следующем обработчике
            user_state[call.message.chat.id] = {"ticker_name": ticker_name, "exchange": exchange, "current_rate": current_rate}
            # Предполагается, что следующее сообщение пользователя будет точкой входа
            bot.register_next_step_handler_by_chat_id(call.message.chat.id, handle_entry_point)
        else:
            bot.answer_callback_query(call.id, "Произошла ошибка при обработке вашего запроса.")


    def handle_entry_point(message):
        user_data = user_state.get(message.chat.id, {})
        try:
            # Попытка преобразовать полученный текст в числовое значение точки входа
            entry_point = float(message.text)
            # Сохраняем точку входа в данные пользователя
            user_data['entry_point'] = entry_point
            # Запрашиваем следующие данные у пользователя
            bot.send_message(message.chat.id, "Введите тейк-профит:")
            # Регистрируем следующий шаг
            bot.register_next_step_handler(message, handle_take_profit)
        except ValueError:
            # Если пользователь ввел нечисловое значение, просим ввести его заново
            bot.send_message(message.chat.id, "Пожалуйста, введите числовое значение для точки входа.")

    def handle_take_profit(message):
        user_data = user_state.get(message.chat.id, {})
        try:
            take_profit = float(message.text)
            user_data['take_profit'] = take_profit

            # Отправляем сообщение с выбором направления сделки
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Long", callback_data="direction_LONG"),
                types.InlineKeyboardButton("Short", callback_data="direction_SHORT")
            )
            bot.send_message(message.chat.id, "Выберите направление сделки:", reply_markup=markup)
            
            # Переносим обработчик на выбор направления
            bot.register_next_step_handler(message, handle_direction_selection)
        except ValueError:
            bot.send_message(message.chat.id, "Введите числовое значение для тейк-профит.")

    def handle_stop_loss(message):
        user_data = user_state.get(message.chat.id, {})
        if not user_data:
            bot.send_message(message.chat.id, "Ошибка состояния пользователя. Попробуйте заново.")
            return

        try:
            stop_loss = float(message.text)
            user_data['stop_loss'] = stop_loss

            # Используем сохранённое направление
            direction = user_data.get('direction', 'LONG')  # По умолчанию 'LONG' если не выбрано

            # Запись в базу данных
            add_new_ticker(
                ticker_name=user_data['ticker_name'],
                entry_point=user_data['entry_point'],
                take_profit=user_data['take_profit'],
                stop_loss=user_data['stop_loss'],
                current_rate=user_data['current_rate'],
                setup_image_path=user_data.get('setup_image_path', "Пропущено пользователем"),
                direction=direction
            )

            bot.send_message(message.chat.id, f"Записана сделка: Точка входа - {user_data['entry_point']}, Тейк-профит - {user_data['take_profit']}, Стоп-лосс - {user_data['stop_loss']}, Направление - {direction}")
        except ValueError:
            bot.send_message(message.chat.id, "Введите числовое значение для стоп-лосс.")

    # def handle_entry_point(message):
    #     user_data = user_state.get(message.chat.id, {})
    #     try:
    #         entry_point = float(message.text)
    #         bot.send_message(message.chat.id, "Введите тейк-профит:")
    #         # Сохраняем точку входа
    #         user_data['entry_point'] = entry_point
    #         # Регистрируем следующий шаг
    #         bot.register_next_step_handler(message, handle_take_profit)
    #     except ValueError:
    #         bot.send_message(message.chat.id, "Введите числовое значение для точки входа.")


    # Обработчик для текста после запроса на изображение
    @bot.message_handler(func=lambda message: True)  # Это должно быть более специфично
    def handle_text_after_image_request(message):
        if message.chat.id in user_state and 'ticker_name' in user_state[message.chat.id]:
            process_entry_point(message, user_state[message.chat.id]['ticker_name'], user_state[message.chat.id]['exchange'], user_state[message.chat.id]['current_rate'])
        else:
            # Обработка других случаев или игнорирование сообщения
            pass

    # Обработчик для текста после запроса на изображение
    # @bot.message_handler(func=lambda message: True)  # Это должно быть более специфично
    # def handle_text_after_image_request(message):
    #     # Здесь должна быть логика определения, что пользователь отвечает на запрос изображения
    #     process_setup_image(bot, message, cached_ticker_name, cached_exchange, cached_current_rate)

    @bot.callback_query_handler(func=lambda call: call.data == 'new_ticker')
    def new_ticker_callback(bot, call):
        initiate_add_ticker(bot, call)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'skip')
    def handle_skip(call):
        bot.answer_callback_query(call.id, "Шаг пропущен.")
        bot.send_message(call.message.chat.id, "Вы пропустили этап ввода изображения сетапа. Пожалуйста, введите следующие данные.")

    # Пример последующего шага, может требовать дополнительной настройки
    @bot.callback_query_handler(func=lambda call: call.data.startswith('setup_'))
    def process_setup(call):
        # Предполагаем, что setup_data разбирается на нужные компоненты
        _, ticker_name, exchange = call.data.split('_')[1:]
        bot.send_message(call.message.chat.id, f"Введите точку входа для {ticker_name} на бирже {exchange}.")


    @bot.callback_query_handler(func=lambda call: call.data == 'cancel')
    def handle_cancel(call):
        bot.answer_callback_query(call.id, "Операция отменена.")
        bot.send_message(call.message.chat.id, "Операция отменена пользователом.")
    


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
