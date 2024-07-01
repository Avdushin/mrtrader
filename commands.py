from telebot import types, apihelper
from db import confirm_entry
from tickers import *
from ROI import calculate_roi
from config import PREFERRED_CHAT_ID, ALARM_CHAT_ID, ALARM_THEME_ID
from decimal import Decimal
from urllib.parse import urlparse
import mysql.connector
import os

# Global variable to track selected trades
selected_trades = set()

def register_handlers(bot):
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        logging.info(f"Received chat ID: {chat_id}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton("📈 Тикеры"), types.KeyboardButton("Архив сделок"), types.KeyboardButton("ℹ️ Помощь"))
        try:
            bot.send_message(chat_id, """Привет!
Я Mr. Trader - бот, который поможет торговать тебе и заработать мильоны тысяч зелёных бумажек!
Мои создатели просят меня мониторить различные токены, а я в свою очередь делюсь оперативной информацией по всем точкам входа с тобой!
Удачной торговли!""", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
        except apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send message in thread: {e}")
            bot.send_message(chat_id, """Привет!
Я Mr. Trader - бот, который поможет торговать тебе и заработать мильоны тысяч зелёных бумажек!
Мои создатели просят меня мониторить различные токены, а я в свою очередь делюсь оперативной информацией по всем точкам входа с тобой!
Удачной торговли!""", reply_markup=markup)

    @bot.message_handler(commands=['tickers'])
    @bot.message_handler(func=lambda message: message.text == "📈 Тикеры")
    def ticker_handler(message):
        manage_tickers(bot, message)

    @bot.message_handler(commands=['archive'])
    @bot.message_handler(func=lambda message: message.text == "Архив сделок")
    def show_archive(message):
        show_archive_tickers_list(bot, message)

    @bot.message_handler(commands=['help'])
    @bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
    def help_handler(message):
        bot.send_message(ALARM_CHAT_ID, "Если у вас появились вопросы, свяжитесь с автором бота: @Itdobro", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("archive_"))
    def show_archived_trade(call):
        trade_id = int(call.data.split('_')[1])
        connection = db.get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT * FROM archive WHERE id = %s", (trade_id,))
            trade = cursor.fetchone()
            if trade:
                leverage = 10
                potential = abs(int(((trade[3] / trade[2] - 1) * leverage * 100)))

                info = (
                    f"─────────────────────\n"
                    f"<b>🔖 Тикер:</b> <code>{trade[1]}</code>\n"
                    f"─────────────────────\n"
                    f"<b>🎯 Точка входа:</b> <code>{Decimal(trade[2])}</code>\n"
                    f"<b>📈 Тейк-профит:</b> <code>{Decimal(trade[3])}</code>\n"
                    f"<b>📉 Стоп-лосс:</b> <code>{Decimal(trade[4])}</code>\n"
                    f"<b>💹 Текущий курс:</b> <code>{Decimal(trade[5])}</code>\n"
                    f"<b>📅 Дата закрытия:</b> <code>{trade[8].strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"<b>📝 Статус:</b> <code>{trade[9]}</code>\n"
                    f"<b>🚀 Потенциал:</b> <code>{potential}% с плечом {leverage}X</code>\n"
                    f"─────────────────────"
                )

                parsed_url = urlparse(trade[6])
                if trade[6] and (os.path.exists(trade[6]) or parsed_url.scheme in ('http', 'https')):
                    if os.path.exists(trade[6]):
                        with open(trade[6], 'rb') as photo:
                            bot.send_photo(config.ALARM_CHAT_ID, photo, caption=info, parse_mode='HTML', message_thread_id=config.ALARM_THEME_ID)
                    else:
                        bot.send_photo(config.ALARM_CHAT_ID, trade[6], caption=info, parse_mode='HTML', message_thread_id=config.ALARM_THEME_ID)
                else:
                    bot.send_message(config.ALARM_CHAT_ID, info, parse_mode="HTML", message_thread_id=config.ALARM_THEME_ID)
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
        markup.add(types.InlineKeyboardButton("Да", callback_data="confirm_clear_all"),
                   types.InlineKeyboardButton("Нет", callback_data="cancel_clear_all"))
        bot.send_message(ALARM_CHAT_ID, "Вы действительно хотите очистить архив?", reply_markup=markup, message_thread_id=config.ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_clear_all")
    def clear_all_archive(call):
        delete_all_archive_trades(bot, call)

    # @bot.callback_query_handler(func=lambda call: call.data == "confirm_clear_all")
    # def clear_all_archive(call):
    #     db.delete_all_archived_trades()
    #     bot.answer_callback_query(call.id, "Архив сделок полностью очищен.")
    #     bot.send_message(ALARM_CHAT_ID, "Все сделки из архива удалены.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_clear_all")
    def cancel_clear_all(call):
        bot.answer_callback_query(call.id, "Очистка архива отменена.")
        bot.send_message(ALARM_CHAT_ID, "Очистка архива сделок отменена.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_archive_"))
    def delete_selected_archived(call):
        trade_id = int(call.data.split('_')[2])
        setup_image_path = db.get_archive_setup_image_path(trade_id)
        
        db.delete_archived_trade(trade_id)
        
        if setup_image_path and os.path.exists(setup_image_path):
            os.remove(setup_image_path)
        
        bot.answer_callback_query(call.id, "Архивная сделка удалена.")
        bot.send_message(ALARM_CHAT_ID, "Сделка успешно удалена из архива.", message_thread_id=ALARM_THEME_ID)

    # @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_archive_"))
    # def delete_selected_archived(call):
    #     trade_id = int(call.data.split('_')[2])
    #     setup_image_path = db.get_archive_setup_image_path(trade_id)
        
    #     # Удаление сделки из архива
    #     db.delete_archived_trade(trade_id)
        
    #     # Удаление изображения, если оно существует
    #     if setup_image_path and os.path.exists(setup_image_path):
    #         os.remove(setup_image_path)
        
    #     bot.answer_callback_query(call.id, "Архивная сделка удалена.")
    #     bot.send_message(ALARM_CHAT_ID, "Сделка успешно удалена из архива.", message_thread_id=ALARM_THEME_ID)

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
                markup.add(types.InlineKeyboardButton(f"{ticker} - {status}", callback_data=f"delete_archive_{id}"))
            markup.add(types.InlineKeyboardButton("Очистить архив", callback_data="clear_all_archive"))
            bot.send_message(ALARM_CHAT_ID, "Выберите сделки для удаления или очистите весь архив:", reply_markup=markup, message_thread_id=ALARM_THEME_ID)
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
        bot.send_message(ALARM_CHAT_ID, "Выбранные сделки успешно удалены из архива.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete_selected")
    def cancel_delete_selected(call):
        selected_trades.clear()
        bot.answer_callback_query(call.id, "Удаление выбранных сделок отменено.")
        bot.send_message(ALARM_CHAT_ID, "Удаление выбранных сделок отменено.", message_thread_id=ALARM_THEME_ID)

    """ TICKERS """
    @bot.message_handler(func=lambda message: message.text == "📈 Тикеры")
    def ticker_handler(message):
        manage_tickers(bot, message)

    @bot.callback_query_handler(func=lambda call: call.data == 'add_ticker')
    def handle_add_ticker(call):
        initiate_add_ticker(bot, call)
    
    @bot.callback_query_handler(func=lambda call: 'direction' in call.data)
    def handle_direction_selection(call):
        process_direction(bot, call)

    @bot.callback_query_handler(func=lambda call: 'exchange' in call.data)
    def handle_exchange_selection_h(call):
        handle_exchange_selection(bot, call)
    
    @bot.callback_query_handler(func=lambda call: call.data == "show_tickers")
    def handle_show_tickers(call):
        show_ticker_list(bot, call.message)

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
        bot.send_message(ALARM_CHAT_ID, "Добавление тикера было отменено.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
    def handle_cancel_delete(call):
        bot.answer_callback_query(call.id, "Удаление отменено.")
        bot.send_message(ALARM_CHAT_ID, "Удаление тикера отменено.", message_thread_id=ALARM_THEME_ID)

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
        chat_id = message.chat.id
        try:
            msg_thread_id = message.reply_to_message.message_thread_id
        except AttributeError:
            msg_thread_id = "General"
        bot.reply_to(message, f"Chat ID этого чата: `{chat_id}`\n ID топика: `{msg_thread_id}`", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_entry_"))
    def confirm_entry_handler(call):
        ticker_id = int(call.data.split('_')[2])
        confirm_entry(ticker_id)
        bot.answer_callback_query(call.id, "Вход в сделку подтвержден.")

        # Кнопка "Сделки"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Сделки", callback_data="active_trades"))

        bot.send_message(ALARM_CHAT_ID, "Вход в сделку подтвержден. Будут отправлены только уведомления о тейк-профите или стоп-лоссе.", reply_markup=markup, message_thread_id=ALARM_THEME_ID)

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

    @bot.callback_query_handler(func=lambda call: call.data.startswith("trade_info_"))
    def trade_info(call):
        trade_id = int(call.data.split('_')[2])
        trade = db.get_trade_details(trade_id)
        if trade:
            leverage = 10
            potential = abs(int(((trade['take_profit'] / trade['entry_point'] - 1) * leverage * 100)))

            info = (
                f"─────────────────────\n"
                f"<b>🔖 Тикер:</b> <code>{trade['ticker']}</code>\n"
                f"─────────────────────\n"
                f"<b>🔄 Направление:</b> <code>{trade['direction']}</code>\n"
                f"<b>🎯 Точка входа (ТВХ):</b> <code>{Decimal(trade['entry_point'])}</code>\n"
                f"<b>📈 Тейк-профит:</b> <code>{Decimal(trade['take_profit'])}</code>\n"
                f"<b>📉 Стоп-лосс:</b> <code>{Decimal(trade['stop_loss'])}</code>\n"
                f"<b>💹 Текущая стоимость:</b> <code>${Decimal(trade['current_rate'])}</code>\n"
                f"<b>📝 Статус:</b> {'Активна' if trade['entry_confirmed'] else 'Неактивна'}\n"
                f"<b>🚀 Потенциал:</b> <code>{potential}% с плечом {leverage}X</code>\n"
                f"─────────────────────"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Выйти из сделки", callback_data=f"cancel_trade_{trade['id']}"))

            parsed_url = urlparse(trade['setup_image_path'])
            if trade['setup_image_path'] and (os.path.exists(trade['setup_image_path']) or parsed_url.scheme in ('http', 'https')):
                if os.path.exists(trade['setup_image_path']):
                    with open(trade['setup_image_path'], 'rb') as photo:
                        bot.send_photo(ALARM_CHAT_ID, photo, caption=info, parse_mode='HTML', reply_markup=markup, message_thread_id=ALARM_THEME_ID)
                else:
                    bot.send_photo(ALARM_CHAT_ID, trade['setup_image_path'], caption=info, parse_mode='HTML', reply_markup=markup, message_thread_id=ALARM_THEME_ID)
            else:
                bot.send_message(ALARM_CHAT_ID, info, parse_mode='HTML', reply_markup=markup, message_thread_id=ALARM_THEME_ID)
        else:
            bot.send_message(ALARM_CHAT_ID, "Сделка не найдена.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_trade_"))
    def cancel_trade(call):
        trade_id = int(call.data.split('_')[2])
        db.cancel_trade(trade_id)
        bot.answer_callback_query(call.id, "Сделка отменена.")
        bot.send_message(ALARM_CHAT_ID, "Сделка успешно отменена.", message_thread_id=ALARM_THEME_ID)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delay_entry_"))
    def handle_delay_entry(call):
        delay_entry(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("mute_entry_"))
    def handle_mute_entry(call):
        mute_entry(bot, call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_mute_"))
    def handle_set_mute(call):
        set_mute(bot, call)

def delete_all_archive_trades(bot, call):
    image_paths = db.get_all_archive_image_paths()
    for path in image_paths:
        if path and os.path.exists(path):
            os.remove(path)
    
    db.delete_all_archived_trades()
    bot.answer_callback_query(call.id, "Архив сделок полностью очищен.")
    bot.send_message(ALARM_CHAT_ID, "Все сделки из архива удалены.", message_thread_id=ALARM_THEME_ID)
