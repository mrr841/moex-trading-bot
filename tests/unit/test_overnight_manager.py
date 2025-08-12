import pytest
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch
from src.overnight_manager import OvernightManager

class TestOvernightManager:
    @pytest.fixture
    def setup_manager(self):
        config = {
            'overnight': {
                'leverage_close_time': time(18, 40),
                'min_time_to_close': timedelta(minutes=30)
            },
            'tickers': ['SBER', 'GAZP']
        }
        return OvernightManager(config)

    @pytest.mark.parametrize("current_time,expected", [
        (datetime(2023,1,1,10,0), False),  # Утро
        (datetime(2023,1,1,18,30), True),  # Перед закрытием
        (datetime(2023,1,1,18,45), True),  # После времени закрытия
    ])
    def test_should_close_leverage(self, setup_manager, current_time, expected):
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            assert setup_manager.should_close_leverage() == expected

    def test_prepare_overnight_positions(self, setup_manager):
        mock_executor = MagicMock()
        mock_executor.get_portfolio.return_value = {
            'positions': [
                {'ticker': 'SBER', 'balance': 10, 'leveraged': False},
                {'ticker': 'GAZP', 'balance': 5, 'leveraged': True},
            ],
            'cash': 50000
        }
        
        setup_manager.prepare_overnight_positions(mock_executor)
        
        # Проверяем что закрыли позиции с плечом
        mock_executor.close_position.assert_called_once_with('GAZP')
        # Проверяем что купили акции без плеча
        mock_executor.buy.assert_called_once()

    @patch('src.overnight_manager.is_holiday')
    def test_holiday_behavior(self, mock_holiday, setup_manager):
        mock_holiday.return_value = True
        mock_executor = MagicMock()
        
        setup_manager.prepare_overnight_positions(mock_executor)
        
        # В праздники не должно быть покупки новых акций
        mock_executor.buy.assert_not_called()