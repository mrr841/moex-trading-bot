from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict

@dataclass
class TickerData:
    """Данные тикера с MOEX"""
    open: float
    high: float
    low: float
    close: float
    volume: int
    time: datetime
    ticker: str
    board: str = "TQBR"  # Режим торгов
    lot_size: int = 1     # Размер лота

@dataclass
class Order:
    """Ордер (Тинькофф или MOEX)"""
    order_id: str
    ticker: str
    figi: str            # Для Тинькофф API
    direction: str       # 'buy'/'sell'
    price: float
    quantity: int
    status: str          # 'new', 'filled', 'canceled'
    account_id: str      # Идентификатор счёта

@dataclass
class Signal:
    """Торговый сигнал"""
    ticker: str
    action: str          # 'buy', 'sell', 'hold'
    confidence: float    # 0.0–1.0
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@dataclass
class Position:
    """Открытая позиция"""
    ticker: str
    figi: str
    entry_price: float
    current_price: float
    quantity: int
    pnl: float
    pnl_percent: float