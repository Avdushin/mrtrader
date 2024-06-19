from unittest.mock import patch, MagicMock
import unittest
import tickers
import bot
import config

class TestPriceMonitoring(unittest.TestCase):
    @patch('tickers.get_current_price', return_value=10009.9)  # Примерно 0.001% от 10000
    @patch('bot.bot.send_message')  # Мокируем метод send_message объекта bot
    def test_price_alerts(self, mock_send_message, mock_get_current_price):
        # Запускаем мониторинг цен
        tickers.monitor_prices()
        # Проверяем, что метод send_message был вызван
        mock_send_message.assert_called_once()

if __name__ == '__main__':
    unittest.main()
