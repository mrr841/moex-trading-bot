# scr/core/bot.py
import asyncio
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum, auto

from ..data.data_handler import DataHandler
from ..managers.strategy_manager import StrategyManager
from ..managers.risk_manager import RiskManager
from ..trading.trade_executor import TradeExecutor
from .state_manager import StateManager, BotState  # чтобы экспортировать BotState из этого модуля

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    TRAIN = auto()
    PAPER = auto()
    REAL = auto()


@dataclass
class BotConfig:
    """Типизированный конфиг, используемый внутри бота."""
    tickers: List[str]
    max_active_positions: int
    timeframe: str
    mode: TradingMode


class TradingBot:
    """Основной класс торгового бота."""

    def __init__(self, config: Dict):
        self.raw_config: Dict = config
        self.config: BotConfig = self._validate_config(config)

        self.state = StateManager()
        self.data_handler: Optional[DataHandler] = None
        self.strategy_manager: Optional[StrategyManager] = None
        self.risk_manager: Optional[RiskManager] = None
        self.trade_executor: Optional[TradeExecutor] = None

        self._shutdown_event = asyncio.Event()
        self._main_loop_task: Optional[asyncio.Task] = None

    def _validate_config(self, config: Dict) -> BotConfig:
        required_keys = {'tickers', 'max_active_positions', 'timeframe', 'mode'}
        missing = required_keys - set(config.keys())
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")

        try:
            mode = TradingMode[config['mode'].upper()]
        except Exception:
            raise ValueError(f"Invalid trading mode: {config.get('mode')}")

        return BotConfig(
            tickers=config['tickers'],
            max_active_positions=config['max_active_positions'],
            timeframe=config['timeframe'],
            mode=mode
        )

    async def run(self) -> None:
        logger.info(f"Starting bot in {self.config.mode.name} mode")

        # Передаем data_handler во второй аргумент TradeExecutor
        async with DataHandler(self.raw_config) as data_handler, \
                   TradeExecutor(self.raw_config, data_handler) as trade_executor:

            self.data_handler = data_handler
            self.trade_executor = trade_executor

            self.strategy_manager = StrategyManager(self.raw_config, self.data_handler)
            self.risk_manager = RiskManager(self.raw_config)

            self._main_loop_task = asyncio.create_task(self._main_loop())
            await self._shutdown_event.wait()

            logger.info("Bot shutdown completed")

    async def _main_loop(self) -> None:
        try:
            while not self._shutdown_event.is_set():
                market_data = await self._fetch_market_data()
                signals = await self.strategy_manager.analyze(market_data)
                approved_signals = self.risk_manager.validate_signals(
                    signals,
                    self.state.positions
                )
                execution_results = await self.trade_executor.execute(approved_signals)
                await self.state.update(execution_results)
                await asyncio.sleep(self._get_loop_interval())
        except Exception as e:
            logger.critical(f"Main loop failed: {str(e)}", exc_info=True)
            await self.shutdown()

    async def _fetch_market_data(self) -> Dict:
        timeframe = self.config.timeframe
        tasks = [
            self.data_handler.get_ticker_data(ticker, timeframe)
            for ticker in self.config.tickers
        ]
        results = await asyncio.gather(*tasks)
        return {ticker: data for ticker, data in zip(self.config.tickers, results)}

    def _get_loop_interval(self) -> int:
        tf = self.config.timeframe
        if isinstance(tf, str) and tf.endswith('m'):
            try:
                return int(tf[:-1]) * 60 // 2
            except Exception:
                return 60
        return 60

    async def shutdown(self) -> None:
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
                try:
                    await self.trade_executor.close_all_positions()
                except Exception as e:
                    logger.exception("Error while closing positions during shutdown: %s", e)

            logger.info("Resources released")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.run(self.shutdown())
