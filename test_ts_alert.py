# test_ts_alert.py
from telebot import TeleBot
from decimal import Decimal, getcontext, ROUND_DOWN, InvalidOperation
from tickers import send_profit_loss_alert
from config import TOKEN

# Создаем экземпляр бота
global_bot = TeleBot(TOKEN)

# Эмулируем условия, при которых обычно вызывается send_profit_loss_alert
ticker_id = 1
ticker_name = 'TestUSDT'
exchange = 'ByBit'
entry_point = Decimal("1.200")
result_point = Decimal("1.300")  # Это может быть take_profit или stop_loss
current_rate = Decimal("1.250")
direction = "LONG"
message_text = f"🎉 {ticker_name} на бирже {exchange} достиг уровня тейк-профита: ${result_point}."
status = "Прибыль"  # Или "Убыток", в зависимости от ситуации

# Вызываем функцию
send_profit_loss_alert(global_bot, ticker_id, ticker_name, direction, entry_point, result_point, current_rate, message_text, status)

# Эмулируем условия, при которых обычно вызывается send_profit_loss_alert
ticker_id = 1
ticker_name = 'TestUSDT'
exchange = 'ByBit'
entry_point = Decimal("1.200")
result_point = Decimal("0.470")  # Это может быть take_profit или stop_loss
current_rate = Decimal("1.250")
direction = "SHORT"
message_text = f"🛑 {ticker_name} на бирже {exchange} достиг уровня стоп-лосса: ${result_point}."
status = "Убыток"  # Или "Убыток", в зависимости от ситуации

# Вызываем функцию
send_profit_loss_alert(global_bot, ticker_id, ticker_name, direction, entry_point, result_point, current_rate, message_text, status)

# from telebot import TeleBot
# from decimal import Decimal, getcontext, ROUND_DOWN, InvalidOperation
# from PnL import create_pnl_image
# from tickers import send_profit_loss_alert
# from config import TOKEN

# # Создаем экземпляр бота
# global_bot = TeleBot(TOKEN)

# # Эмулируем условия, при которых обычно вызывается send_profit_loss_alert
# ticker_id = 1
# ticker_name='TestUSDT'
# exchange='ByBit'
# entry_point = Decimal("1.200")
# result_point = Decimal("1.300")  # Это может быть take_profit или stop_loss
# current_rate = Decimal("1.250")
# message_text = f"Тестовое сообщение: Тикер достиг цели с результатом {result_point}"
# message_text = f"🎉 {ticker_name} на бирже {exchange} достиг уровня тейк-профита: ${result_point}."
# status = "Прибыль"  # Или "Убыток", в зависимости от ситуации

# # Вызываем функцию
# send_profit_loss_alert(global_bot, ticker_id, entry_point, result_point, current_rate, message_text, status)
