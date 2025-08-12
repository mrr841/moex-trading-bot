import pytest
import time
from src.indicator_engine import IndicatorEngine
import pandas as pd
import numpy as np

class TestPerformance:
    @pytest.fixture
    def large_dataset(self):
        # Генерируем большой набор данных для тестов
        size = 10000  # 10k записей
        return pd.DataFrame({
            'open': np.random.uniform(100, 200, size),
            'high': np.random.uniform(100, 200, size),
            'low': np.random.uniform(100, 200, size),
            'close': np.random.uniform(100, 200, size),
            'volume': np.random.randint(1000, 10000, size)
        })

    def test_indicator_performance(self, large_dataset):
        engine = IndicatorEngine()
        
        start_time = time.time()
        result = engine.calculate_all(large_dataset)
        elapsed = time.time() - start_time
        
        assert not result.empty
        print(f"\nIndicator calculation time: {elapsed:.4f}s")
        
        # Ожидаем что расчет индикаторов займет менее 1 секунды
        assert elapsed < 1.0

    @pytest.mark.parametrize("period", [10, 50, 200])
    def test_sma_performance(self, large_dataset, period):
        start_time = time.time()
        result = IndicatorEngine.calculate_sma(large_dataset['close'], period)
        elapsed = time.time() - start_time
        
        assert len(result) == len(large_dataset)
        print(f"\nSMA-{period} calculation time: {elapsed:.6f}s")
        assert elapsed < 0.1

    def test_full_cycle_performance(self, large_dataset):
        from src.strategy_manager import StrategyManager
        from src.regime_detector import MarketRegimeDetector
        
        detector = MarketRegimeDetector()
        strategy = StrategyManager({})
        
        start_time = time.time()
        regime = detector.detect_regime(large_dataset)
        signals = strategy.generate_signals(large_dataset, regime)
        elapsed = time.time() - start_time
        
        assert not signals.empty
        print(f"\nFull cycle time: {elapsed:.4f}s")
        assert elapsed < 2.0