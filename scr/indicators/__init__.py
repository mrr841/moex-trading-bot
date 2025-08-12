"""
Indicators Module - технические индикаторы и расчеты для торговых стратегий

Содержит:
- Базовые индикаторы (TA-Lib, pandas_ta)
- Пользовательские индикаторы
- Вспомогательные функции для анализа
"""

from .indicator_engine import (
    calculate_adx,
    calculate_atr,
    calculate_ema,
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_volume_profile,
    calculate_macd,
    calculate_support_resistance,
    calculate_sma,
)

from .custom_indicators import (
    fractal_breakout_detector,
    volume_spike_detector,
    trend_intensity_index,
    anchored_vwap,
    heikin_ashi_smoothed,
    cumulative_delta,
    detect_trend,
    detect_liquidity_regime,
    detect_volatility_regime,
)

import logging
from typing import List, Tuple

__all__ = [
    # Из indicator_engine
    'calculate_adx',
    'calculate_atr',
    'calculate_ema',
    'calculate_rsi',
    'calculate_bollinger_bands',
    'calculate_volume_profile',
    'calculate_macd',
    'calculate_support_resistance',
    'calculate_sma',
    
    # Из custom_indicators
    'fractal_breakout_detector',
    'volume_spike_detector',
    'trend_intensity_index',
    'anchored_vwap',
    'heikin_ashi_smoothed',
    'cumulative_delta',
    'detect_trend',
    'detect_liquidity_regime',
    'detect_volatility_regime',
]

__version__ = '1.1.0'

_logger = logging.getLogger(__name__)
_logger.info(f'Indicators module v{__version__} initialized')

DEFAULT_WINDOW_SIZES = {
    'short': 14,
    'medium': 50,
    'long': 200,
}

def list_available_indicators() -> List[Tuple[str, str]]:
    """Возвращает список доступных индикаторов в виде (код, описание)"""
    return [
        ('ADX', 'Average Directional Index'),
        ('ATR', 'Average True Range'),
        ('EMA', 'Exponential Moving Average'),
        ('RSI', 'Relative Strength Index'),
        ('BBANDS', 'Bollinger Bands'),
        ('VPROF', 'Volume Profile'),
        ('MACD', 'Moving Average Convergence Divergence'),
        ('SUPPORT_RESISTANCE', 'Support and Resistance Levels'),
        ('SMA', 'Simple Moving Average'),
        ('FRACTAL', 'Fractal Breakout Detector'),
        ('VSPIKE', 'Volume Spike Detector'),
        ('TII', 'Trend Intensity Index'),
        ('ANCH_VWAP', 'Anchored VWAP'),
        ('HA_SMOOTH', 'Heikin Ashi Smoothed'),
        ('CUM_DELTA', 'Cumulative Delta'),
        ('TREND_DETECT', 'Trend Detection'),
        ('LIQUIDITY_REGIME', 'Liquidity Regime Detection'),
        ('VOLATILITY_REGIME', 'Volatility Regime Detection'),
    ]

def validate_indicator_params(params: dict) -> bool:
    """Простая валидация словаря параметров индикатора"""
    required = ['window', 'name']
    return all(k in params for k in required)
