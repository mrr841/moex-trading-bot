import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum, auto

from ..data.data_handler import DataHandler
from ..managers.strategy_manager import StrategyManager
from ..managers.risk_manager import RiskManager
from ..trading.trade_executor import TradeExecutor
from .state_manager import StateManager

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    TRAIN = auto()
    PAPER = auto()
    REAL = auto()

@dataclass
class BotConfig:
    tickers: list[str]
    max_active_positions: int
    timeframe: str
    mode: TradingMode

class TradingBot:
    """Основной класс торгового бота"""
    
    def __init__(self, config: Dict):
        self.config = self._validate_config(config)
        self.state = StateManager()
        self.data_handler: Optional[DataHandler] = None
        self.strategy_manager: Optional[StrategyManager] = None
        self.risk_manager: Optional[RiskManager] = None
        self.trade_executor: Optional[TradeExecutor] = None
        
        self._shutdown_event = asyncio.Event()
        self._main_loop_task: Optional[asyncio.Task] = None

    def _validate_config(self, config: Dict) -> BotConfig:
        """Проверка и преобразование конфигурации"""
        required_keys = {'tickers', 'max_active_positions', 'timeframe', 'mode'}
        if not required_keys.issubset(config.keys()):
            raise ValueError(f"Missing required config keys: {required_keys - config.keys()}")
            
        try:
            mode = TradingMode[config['mode'].upper()]
        except KeyError:
            raise ValueError(f"Invalid trading mode: {config['mode']}")
            
        return BotConfig(
            tickers=config['tickers'],
            max_active_positions=config['max_active_positions'],
            timeframe=config['timeframe'],
            mode=mode
        )

    async def run(self) -> None:
        """Основной цикл работы бота"""
        logger.info(f"Starting bot in {self.config.mode.name} mode")
        
        async with DataHandler(self.config) as self.data_handler, \
                 TradeExecutor(self.config) as self.trade_executor:
            
            self.strategy_manager = StrategyManager(self.config, self.data_handler)
            self.risk_manager = RiskManager(self.config)
            
            self._main_loop_task = asyncio.create_task(self._main_loop())
            await self._shutdown_event.wait()
            
            logger.info("Bot shutdown completed")

    async def _main_loop(self) -> None:
        """Цикл обработки данных и торговли"""
        try:
            while not self._shutdown_event.is_set():
                # 1. Получение данных
                market_data = await self._fetch_market_data()
                
                # 2. Анализ стратегии
                signals = await self.strategy_manager.analyze(market_data)
                
                # 3. Проверка рисков
                approved_signals = self.risk_manager.validate_signals(
                    signals, 
                    self.state.current_positions
                )
                
                # 4. Исполнение сделок
                execution_results = await self.trade_executor.execute(approved_signals)
                
                # 5. Обновление состояния
                self.state.update(execution_results)
                
                # 6. Пауза между итерациями
                await asyncio.sleep(self._get_loop_interval())
                
        except Exception as e:
            logger.critical(f"Main loop failed: {str(e)}", exc_info=True)
            await self.shutdown()

    async def _fetch_market_data(self) -> Dict:
        """Получение рыночных данных для всех тикеров"""
        tasks = [
            self.data_handler.get_ticker_data(ticker, self.config.timeframe)
            for ticker in self.config.tickers
        ]
        return {
            ticker: data 
            for ticker, data in zip(
                self.config.tickers, 
                await asyncio.gather(*tasks)
            )
        }

    def _get_loop_interval(self) -> int:
        """Определение интервала между итерациями"""
        if self.config.timeframe.endswith('m'):
            return int(self.config.timeframe[:-1]) * 60 // 2
        return 60  # По умолчанию 1 минута

    async def shutdown(self) -> None:
        """Корректное завершение работы бота"""
        if not self._shutdown_event.is_set():
            logger.info("Shutdown initiated...")
            self._shutdown_event.set()
            
            if self._main_loop_task:
                self._main_loop_task.cancel()
                try:
                    await self._main_loop_task
                except asyncio.CancelledError:
                    pass
                
            if self.trade_executor:
                await self.trade_executor.close_all_positions()
                
            logger.info("Resources released")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.run(self.shutdown())