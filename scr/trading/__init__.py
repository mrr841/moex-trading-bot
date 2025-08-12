"""
Trading Module - исполнение торговых операций и управление ордерами

Содержит:
- Исполнитель торговых операций (TradeExecutor)
- Модели ордеров и сделок
- Адаптеры для разных брокеров
"""

from .trade_executor import (
    TradeExecutor,
    Order,
    ExecutionReport,
    OrderStatus,
    OrderType,
    BrokerType
)

from typing import Dict, List, Optional
from enum import Enum
import logging
from dataclasses import dataclass

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

class TradeError(Exception):
    """Базовый класс ошибок торгового модуля"""
    pass

class BrokerType(Enum):
    TINKOFF = 'tinkoff'
    MOEX = 'moex'
    BINANCE = 'binance'

@dataclass
class Order:
    """Модель торгового ордера"""
    order_id: str
    ticker: str
    order_type: OrderType
    price: float
    quantity: int
    timestamp: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: Optional[float] = None
    reason: Optional[str] = None

@dataclass
class ExecutionReport:
    """Отчет об исполнении ордера"""
    order_id: str
    execution_time: datetime
    filled_quantity: int
    fill_price: float
    commission: float
    remaining_quantity: int

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