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
    calculate_macd
)

from .custom_indicators import (
    fractal_breakout_detector,
    volume_spike_detector,
    trend_intensity_index,
    anchored_vwap,
    heikin_ashi_smoothed
)

import logging
from typing import List, Tuple
import numpy as np

__all__ = [
    # Из indicator_engine
    'calculate_adx',
    'calculate_atr',
    'calculate_ema',
    'calculate_rsi',
    'calculate_bollinger_bands',
    'calculate_volume_profile',
    'calculate_macd',
    
    # Из custom_indicators
    'fractal_breakout_detector',
    'volume_spike_detector',
    'trend_intensity_index',
    'anchored_vwap',
    'heikin_ashi_smoothed'
]

__version__ = '1.1.0'

# Настройка логгера модуля
_logger = logging.getLogger(__name__)
_logger.info(f'Indicators module v{__version__} initialized')

# Константы модуля
DEFAULT_WINDOW_SIZES = {
    'short': 14,
    'medium': 50,
    'long': 200
}

def list_available_indicators() -> List[Tuple[str, str]]:
    """Возвращает список доступных индикаторов"""
    return [
        ('ADX', 'Average Directional Index'),
        ('ATR', 'Average True Range'),
        ('RSI', 'Relative Strength Index'),
        ('BBANDS', 'Bollinger Bands'),
        ('VPROF', 'Volume Profile'),
        ('FRACTAL', 'Fractal Breakout Detector'),
        ('VSPIKE', 'Volume Spike Detector')
    ]

def validate_indicator_params(params: dict) -> bool:
    """Валидация параметров индикатора"""
    required = ['window', 'name']
    return all(k in params for k in required)