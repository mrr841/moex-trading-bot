"""
Data module - handles all market data operations including:
- Real-time and historical data fetching
- Local caching
- API integrations (MOEX ISS, Tinkoff Invest)
"""

from .data_handler import DataHandler
from .cache_manager import CacheManager

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

__all__ = ['DataHandler', 'CacheManager', 'MarketData', 'Candle', 'Orderbook', 'TickerInfo']
__version__ = '1.0.0'

# Инициализация логгера модуля
_logger = logging.getLogger(__name__)
_logger.info(f"Initializing data module v{__version__}")

# Константы модуля
DATA_ROOT = Path(__file__).parent.parent.parent / 'data'
CACHE_VALIDITY = {
    'tickers': 86400,      # 24 часа
    'candles': 3600,       # 1 час
    'orderbook': 300       # 5 минут
}

# Определение типов данных
@dataclass
class Candle:
    """Свечные данные"""
    open: float
    high: float
    low: float
    close: float
    volume: float
    time: str
    ticker: str

@dataclass
class Orderbook:
    """Данные стакана"""
    bids: List[Dict[str, float]]
    asks: List[Dict[str, float]]
    timestamp: int

@dataclass
class TickerInfo:
    """Информация о тикере"""
    ticker: str
    name: str
    lot_size: int
    min_step: float
    currency: str

MarketData = Dict[str, Any]  # Общий тип для рыночных данных

def validate_data_dir() -> bool:
    """Проверка доступности директории для данных"""
    try:
        DATA_ROOT.mkdir(exist_ok=True)
        (DATA_ROOT / '.gitkeep').touch(exist_ok=True)
        return True
    except Exception as e:
        _logger.critical(f"Data directory setup failed: {str(e)}")
        return False

# Автопроверка при импорте
if not validate_data_dir():
    raise RuntimeError("Data directory initialization failed")