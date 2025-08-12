from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging
from enum import Enum, auto
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    OPEN = auto()
    CLOSED = auto()
    PENDING = auto()

class OrderType(Enum):
    BUY = auto()
    SELL = auto()
    STOP_LOSS = auto()
    TAKE_PROFIT = auto()

@dataclass
class Position:
    ticker: str
    entry_price: float
    current_price: float
    volume: int
    status: PositionStatus
    open_time: datetime
    close_time: Optional[datetime] = None
    pnl: float = 0.0
    orders: List['Order'] = field(default_factory=list)

@dataclass
class Order:
    order_id: str
    ticker: str
    order_type: OrderType
    price: float
    volume: int
    timestamp: datetime
    executed: bool = False

class BotState(Enum):
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    SHUTTING_DOWN = auto()
    ERROR = auto()

class StateManager:
    """Менеджер состояния торгового бота"""
    
    def __init__(self):
        self._state = BotState.STARTING
        self.positions: Dict[str, Position] = {}
        self._lock = asyncio.Lock()
        self._state_handlers = {
            BotState.STARTING: self._handle_starting,
            BotState.RUNNING: self._handle_running,
            BotState.PAUSED: self._handle_paused,
            BotState.SHUTTING_DOWN: self._handle_shutting_down,
            BotState.ERROR: self._handle_error
        }
        
    @property
    def current_state(self) -> BotState:
        return self._state
        
    @current_state.setter
    def current_state(self, new_state: BotState):
        logger.info(f"State changed: {self._state.name} -> {new_state.name}")
        self._state = new_state
        asyncio.create_task(self._state_handlers[new_state]())

    async def update(self, execution_results: List[Order]):
        """Обновление состояния на основе исполненных ордеров"""
        async with self._lock:
            for order in execution_results:
                if not order.executed:
                    continue
                    
                if order.order_type in (OrderType.BUY, OrderType.SELL):
                    await self._update_positions(order)

    async def _update_positions(self, order: Order):
        """Обновление позиций на основе ордера"""
        position = self.positions.get(order.ticker)
        
        if order.order_type == OrderType.BUY:
            if position and position.status == PositionStatus.OPEN:
                # Усреднение позиции
                total_volume = position.volume + order.volume
                position.entry_price = (
                    (position.entry_price * position.volume + 
                     order.price * order.volume) / total_volume
                )
                position.volume = total_volume
            else:
                # Новая позиция
                self.positions[order.ticker] = Position(
                    ticker=order.ticker,
                    entry_price=order.price,
                    current_price=order.price,
                    volume=order.volume,
                    status=PositionStatus.OPEN,
                    open_time=order.timestamp
                )
                
        elif order.order_type == OrderType.SELL:
            if position and position.status == PositionStatus.OPEN:
                # Закрытие позиции
                position.status = PositionStatus.CLOSED
                position.close_time = order.timestamp
                position.pnl = (order.price - position.entry_price) * order.volume
                
        logger.debug(f"Position updated: {order.ticker} {order.order_type.name}")

    async def get_open_positions(self) -> List[Position]:
        """Получение всех открытых позиций"""
        async with self._lock:
            return [
                pos for pos in self.positions.values() 
                if pos.status == PositionStatus.OPEN
            ]

    async def get_position(self, ticker: str) -> Optional[Position]:
        """Получение позиции по тикеру"""
        async with self._lock:
            return self.positions.get(ticker)

    async def reset(self):
        """Сброс состояния (для тестов)"""
        async with self._lock:
            self.positions.clear()
            self.current_state = BotState.STARTING

    async def _handle_starting(self):
        """Обработчик состояния STARTING"""
        logger.info("Initializing state manager...")

    async def _handle_running(self):
        """Обработчик состояния RUNNING"""
        logger.info("Bot is now running")

    async def _handle_paused(self):
        """Обработчик состояния PAUSED"""
        logger.warning("Bot paused - no new positions will be opened")

    async def _handle_shutting_down(self):
        """Обработчик состояния SHUTTING_DOWN"""
        logger.info("Shutting down state manager...")
        open_positions = await self.get_open_positions()
        if open_positions:
            logger.warning(f"{len(open_positions)} positions remain open")

    async def _handle_error(self):
        """Обработчик состояния ERROR"""
        logger.error("Bot entered error state!")
        open_positions = await self.get_open_positions()
        if open_positions:
            logger.critical(f"Emergency! {len(open_positions)} open positions in error state")