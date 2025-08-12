import pytest
from unittest.mock import MagicMock, patch
from src.telegram_interface import TelegramInterface

class TestTelegramInterface:
    @pytest.fixture
    def setup_telegram(self):
        config = {
            'telegram': {
                'token': 'test_token',
                'chat_id': 'test_chat'
            }
        }
        return TelegramInterface(config)

    @patch('src.telegram_interface.requests.post')
    def test_send_notification(self, mock_post, setup_telegram):
        mock_post.return_value.status_code = 200
        
        setup_telegram.send_notification("Test message")
        
        mock_post.assert_called_once()
        assert "Test message" in mock_post.call_args[1]['data']['text']

    @patch('src.telegram_interface.requests.post')
    def test_trade_alert_formatting(self, mock_post, setup_telegram):
        trade_data = {
            'ticker': 'SBER',
            'operation': 'buy',
            'price': 280.5,
            'quantity': 10,
            'amount': 2805,
            'mode': 'без плеча'
        }
        
        setup_telegram.send_trade_alert(trade_data)
        
        message = mock_post.call_args[1]['data']['text']
        assert "SBER" in message
        assert "280.5" in message
        assert "без плеча" in message

    @patch('src.telegram_interface.requests.post')
    def test_error_handling(self, mock_post, setup_telegram):
        mock_post.side_effect = Exception("Connection error")
        
        # Проверяем что исключение обрабатывается
        try:
            setup_telegram.send_notification("Test")
            pytest.fail("Expected exception was not raised")
        except Exception as e:
            assert "Error sending Telegram" in str(e)