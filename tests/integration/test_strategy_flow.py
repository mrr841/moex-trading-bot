import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
from src.strategy_manager import StrategyManager
from src.regime_detector import MarketRegimeDetector
from src.indicator_engine import IndicatorEngine

class TestStrategyFlow:
    @pytest.fixture
    def sample_market_data(self):
        # Генерируем тестовые данные для разных режимов рынка
        date_range = pd.date_range(start=datetime.now(), periods=50, freq='1min')
        
        # Боковик
        sideways = pd.DataFrame({
            'open': [100 + i % 3 for i in range(50)],
            'high': [101 + i % 3 for i in range(50)],
            'low': [99 + i % 3 for i in range(50)],
            'close': [100 + i % 3 for i in range(50)],
            'volume': [1000 + i*10 for i in range(50)]
        }, index=date_range)
        
        # Восходящий тренд
        uptrend = pd.DataFrame({
            'open': [100 + i*0.5 for i in range(50)],
            'high': [101 + i*0.5 for i in range(50)],
            'low': [99 + i*0.5 for i in range(50)],
            'close': [100 + i*0.5 for i in range(50)],
            'volume': [1000 + i*20 for i in range(50)]
        }, index=date_range)
        
        # Нисходящий тренд
        downtrend = pd.DataFrame({
            'open': [100 - i*0.3 for i in range(50)],
            'high': [101 - i*0.3 for i in range(50)],
            'low': [99 - i*0.3 for i in range(50)],
            'close': [100 - i*0.3 for i in range(50)],
            'volume': [1000 + i*15 for i in range(50)]
        }, index=date_range)
        
        return {
            "sideways": sideways,
            "uptrend": uptrend,
            "downtrend": downtrend
        }

    def test_strategy_adaptation_to_regime(self, sample_market_data):
        detector = MarketRegimeDetector()
        strategies = StrategyManager(config={
            "strategies": {
                "sideways": {"max_positions": 3},
                "uptrend": {"take_profit": 0.05},
                "downtrend": {"accumulate": True}
            }
        })
        
        for regime_name, data in sample_market_data.items():
            regime = detector.detect_regime(data)
            signals = strategies.generate_signals(data, regime)
            
            assert not signals.empty
            assert "signal" in signals.columns
            
            # Проверяем что стратегия адаптировалась к режиму
            if regime_name == "uptrend":
                assert any(signals['signal'].str.contains('buy'))
            elif regime_name == "downtrend":
                assert signals['signal'].value_counts().get('accumulate', 0) > 0

    @patch('src.indicator_engine.IndicatorEngine.calculate_all')
    def test_indicator_integration(self, mock_calculate, sample_market_data):
        mock_calculate.return_value = pd.DataFrame({
            'sma_20': [100] * 50,
            'ema_50': [101] * 50,
            'rsi': [60] * 50,
            'atr': [1.5] * 50
        })
        
        detector = MarketRegimeDetector()
        strategies = StrategyManager(config={})
        
        data = sample_market_data["uptrend"]
        regime = detector.detect_regime(data)
        signals = strategies.generate_signals(data, regime)
        
        # Проверяем что индикаторы были использованы
        mock_calculate.assert_called_once()
        assert not signals.empty