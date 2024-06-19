from unittest.mock import patch, MagicMock
import unittest
import tickers
import bot
import config

class TestBotFunctionality(unittest.TestCase):
    @patch('tickers.get_current_price')
    @patch('tickers.db.get_db_connection')
    @patch('bot.bot.send_message')
    def test_entry_point_alerts(self, mock_send_message, mock_db_conn, mock_get_current_price):
        # Настройка моков
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db_conn.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(1, 'BTCUSDT', 10000.0)]
        mock_get_current_price.return_value = 10100.0  # 1% выше точки входа

        # Вызов функции
        tickers.check_entry_points(bot.bot)

        # Проверка вызова send_message с правильными аргументами
        expected_text = f"🚨 BTCUSDT близок к точке входа: 10000.0 (текущая цена: 10100.0)"
        mock_send_message.assert_called_once_with(
            chat_id=config.ADMIN_CHAT_ID,
            text=expected_text
        )

if __name__ == '__main__':
    unittest.main()
