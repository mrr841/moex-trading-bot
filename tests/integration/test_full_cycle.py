import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
from src.main import TradingBot
from src.regime_detector import MarketRegime
from src.strategy_manager import TradingSignal

class TestFullCycle:
    @pytest.fixture
    def mock_components(self):
        # Создаем моки всех компонентов
        data_handler = MagicMock()
        regime_detector = MagicMock()
        strategy_manager = MagicMock()
        risk_manager = MagicMock()
        trade_executor = MagicMock()
        
        # Настраиваем возвращаемые значения
        sample_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 1500, 2000]
        }, index=pd.date_range(start=datetime.now(), periods=3, freq='1min'))
        
        data_handler.get_candles.return_value = sample_data
        regime_detector.detect_regime.return_value = MarketRegime.UPTREND
        strategy_manager.generate_signals.return_value = [
            {"ticker": "SBER", "signal": TradingSignal.BUY, "price": 100.5, "confidence": 0.8}
        ]
        risk_manager.validate_position.return_value = True
        trade_executor.get_portfolio.return_value = {"cash": 10000, "positions": []}
        trade_executor.send_order.return_value = {"status": "filled"}
        
        return {
            "data_handler": data_handler,
            "regime_detector": regime_detector,
            "strategy_manager": strategy_manager,
            "risk_manager": risk_manager,
            "trade_executor": trade_executor
        }

    def test_full_trading_cycle(self, mock_components):
        # Инициализируем бота с моками
        bot = TradingBot(
            config={"tickers": ["SBER"], "max_active_positions": 3},
            data_handler=mock_components["data_handler"],
            regime_detector=mock_components["regime_detector"],
            strategy_manager=mock_components["strategy_manager"],
            risk_manager=mock_components["risk_manager"],
            trade_executor=mock_components["trade_executor"]
        )
        
        # Запускаем один цикл торговли
        bot.run_cycle()
        
        # Проверяем, что все компоненты были вызваны
        mock_components["data_handler"].get_candles.assert_called_once()
        mock_components["regime_detector"].detect_regime.assert_called_once()
        mock_components["strategy_manager"].generate_signals.assert_called_once()
        mock_components["risk_manager"].validate_position.assert_called_once()
        mock_components["trade_executor"].send_order.assert_called_once_with(
            ticker="SBER", operation="buy", quantity=1, price=100.5
        )

    @patch('src.telegram_interface.send_notification')
    def test_telegram_notifications(self, mock_send, mock_components):
        bot = TradingBot(
            config={"tickers": ["SBER"], "telegram_enabled": True},
            data_handler=mock_components["data_handler"],
            trade_executor=mock_components["trade_executor"],
            regime_detector=mock_components["regime_detector"],
            strategy_manager=mock_components["strategy_manager"],
            risk_manager=mock_components["risk_manager"]
        )
        
        bot.run_cycle()
        
        # Проверяем, что уведомление было отправлено
        mock_send.assert_called()
        assert "SBER" in mock_send.call_args[0][0]
        assert "buy" in mock_send.call_args[0][0].lower()