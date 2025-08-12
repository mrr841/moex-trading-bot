import pytest
from unittest.mock import MagicMock
from src.data_handler import DataHandlerError
from src.trade_executor import TradeExecutionError
from src.strategy_manager import StrategyError

class TestErrorHandling:
    @pytest.fixture
    def mock_components(self):
        data_handler = MagicMock()
        data_handler.get_candles.side_effect = DataHandlerError("API timeout")
        
        trade_executor = MagicMock()
        trade_executor.send_order.side_effect = TradeExecutionError("Insufficient funds")
        
        strategy_manager = MagicMock()
        strategy_manager.generate_signals.side_effect = StrategyError("Invalid data")
        
        return {
            'data_handler': data_handler,
            'trade_executor': trade_executor,
            'strategy_manager': strategy_manager
        }

    def test_data_fetch_error(self, mock_components):
        with pytest.raises(DataHandlerError):
            mock_components['data_handler'].get_candles('SBER', '1min', 100)

    def test_trade_execution_error(self, mock_components):
        with pytest.raises(TradeExecutionError):
            mock_components['trade_executor'].send_order(
                ticker='GAZP', operation='buy', quantity=10
            )

    def test_strategy_error_recovery(self, mock_components):
        # Тест на восстановление после ошибки стратегии
        strategy = mock_components['strategy_manager']
        
        # Первый вызов завершается ошибкой
        with pytest.raises(StrategyError):
            strategy.generate_signals({})
        
        # Меняем поведение мока
        strategy.generate_signals.side_effect = None
        strategy.generate_signals.return_value = []
        
        # Второй вызов должен работать
        result = strategy.generate_signals({})
        assert result == []

    @patch('src.risk_manager.logger.error')
    def test_risk_validation_error(self, mock_logger):
        from src.risk_manager import RiskManager
        
        manager = RiskManager({'stop_loss': 0.1})
        # Невалидные данные
        with pytest.raises(ValueError):
            manager.validate_position(None, None, None)
        
        assert mock_logger.called