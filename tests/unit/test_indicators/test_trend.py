import pytest
import numpy as np
from src.indicator_engine.trend_indicators import calculate_ema, calculate_sma, calculate_adx

class TestTrendIndicators:
    @pytest.mark.parametrize("period,expected", [
        (5, [100, 100.2, 100.4, 100.6, 100.8]),
        (10, [100, 100.1, 100.2, 100.3, 100.4])
    ])
    def test_sma(self, sample_candles, period, expected):
        close_prices = sample_candles['close']
        result = calculate_sma(close_prices, period)[:5]
        assert np.allclose(result, expected, rtol=0.1)

    def test_ema(self, sample_candles):
        close_prices = sample_candles['close']
        result = calculate_ema(close_prices, 5)[:5]
        # EMA должен быть более чувствительным к последним данным
        assert result[0] == 100
        assert result[-1] > 100

    def test_adx(self, sample_candles):
        high = sample_candles['high']
        low = sample_candles['low']
        close = sample_candles['close']
        result = calculate_adx(high, low, close, 14)
        assert len(result) == len(close)
        assert 0 <= result[-1] <= 100