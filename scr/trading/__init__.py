"""
Trading Module - исполнение торговых операций и управление ордерами
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging

from .trade_executor import (
    TradeExecutor,
    Order,
    ExecutionReport,
    OrderStatus,
    OrderType,
    BrokerType,
    TradeError
)

__all__ = [
    'TradeExecutor',
    'Order',
    'ExecutionReport',
    'OrderStatus',
    'OrderType',
    'BrokerType',
    'TradeError'
]

__version__ = '1.3.0'

# Настройка логгера модуля
_logger = logging.getLogger(__name__)
_logger.info(f'Trading module v{__version__} initialized')

# Константы модуля
DEFAULT_SLIPPAGE = {
    BrokerType.TINKOFF: 0.001,  # 0.1%
    BrokerType.MOEX: 0.0005,    # 0.05%
    BrokerType.BINANCE: 0.0002  # 0.02%
}

def validate_order(order: Dict) -> bool:
    """Валидация параметров ордера"""
    required = ['ticker', 'order_type', 'price', 'quantity']
    return all(k in order for k in required)