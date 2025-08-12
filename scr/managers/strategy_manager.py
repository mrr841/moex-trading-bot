import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, time
import talib
import asyncio

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Типы торговых сигналов"""
    ENTRY_LONG = auto()     # Вход в длинную позицию
    ENTRY_SHORT = auto()    # Вход в короткую позицию
    EXIT_LONG = auto()      # Выход из длинной позиции
    EXIT_SHORT = auto()     # Выход из короткой позиции
    HOLD = auto()           # Удержание позиции

class StrategyType(Enum):
    """Типы торговых стратегий"""
    TREND_FOLLOWING = auto()   # Трендовая стратегия
    MEAN_REVERSION = auto()    # Стратегия возврата к среднему
    BREAKOUT = auto()          # Стратегия пробоя
    SCALPING = auto()          # Скальпинг стратегия

@dataclass
class TradeSignal:
    """Класс для хранения торгового сигнала"""
    ticker: str
    signal_type: SignalType
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: int = 1
    strategy: StrategyType = StrategyType.TREND_FOLLOWING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
class SignalGenerator:
    """Генератор торговых сигналов на основе технических индикаторов"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_confidence = config.get('min_confidence', 0.65)
        
    async def generate(self, ticker: str, data: pd.DataFrame) -> List[TradeSignal]:
        """
        Генерация сигналов для конкретного тикера
        
        Args:
            ticker: Тикер инструмента
            data: DataFrame с OHLCV данными
            
        Returns:
            Список торговых сигналов
        """
        signals = []
        
        # Пример простой стратегии пересечения MA
        if len(data) >= 20:
            short_ma = data['close'].rolling(window=5).mean()
            long_ma = data['close'].rolling(window=20).mean()
            
            if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
                signals.append(TradeSignal(
                    ticker=ticker,
                    signal_type=SignalType.ENTRY_LONG,
                    price=data['close'].iloc[-1],
                    confidence=0.7
                ))
            elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
                signals.append(TradeSignal(
                    ticker=ticker,
                    signal_type=SignalType.ENTRY_SHORT,
                    price=data['close'].iloc[-1],
                    confidence=0.7
                ))
        
        return signals

class StrategyManager:
    """Ядро генерации торговых сигналов на основе стратегий"""

    def __init__(self, config: Dict, data_handler):
        """
        Инициализация менеджера стратегий
        
        Args:
            config: Конфигурация стратегий
            data_handler: Обработчик данных
        """
        self.config = config
        self.data_handler = data_handler
        self.active_strategies = self._init_strategies()
        self.signals_history = []
        self.confirmation_rules = {
            'volume_confirmation': True,
            'multi_timeframe': False,
            'min_confidence': 0.65
        }

    def _init_strategies(self) -> Dict[StrategyType, Dict]:
        """Инициализация активных стратегий из конфига"""
        strategies = {}
        for strat_config in self.config.get('strategies', []):
            try:
                strat_type = StrategyType[strat_config['type'].upper()]
                strategies[strat_type] = {
                    'params': strat_config.get('params', {}),
                    'weight': strat_config.get('weight', 1.0)
                }
            except KeyError:
                logger.warning(f"Unknown strategy type: {strat_config['type']}")
        return strategies

    async def analyze(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, List[TradeSignal]]:
        """
        Анализ рыночных данных и генерация сигналов
        
        Args:
            market_data: Словарь с DataFrame для каждого тикера
            
        Returns:
            Словарь с сигналами для каждого тикера
        """
        results = {}
        for ticker, data in market_data.items():
            if data.empty:
                continue
                
            signals = []
            for strat_type, config in self.active_strategies.items():
                try:
                    strat_signals = await self._apply_strategy(
                        strat_type, 
                        ticker, 
                        data, 
                        config['params']
                    )
                    signals.extend(strat_signals)
                except Exception as e:
                    logger.error(f"Strategy {strat_type.name} failed for {ticker}: {str(e)}")

            filtered_signals = self._filter_signals(signals)
            confirmed_signals = await self._confirm_signals(filtered_signals)
            self.signals_history.extend(confirmed_signals)
            results[ticker] = confirmed_signals
            
        return results

    async def _apply_strategy(self, 
                            strat_type: StrategyType, 
                            ticker: str, 
                            data: pd.DataFrame,
                            params: Dict) -> List[TradeSignal]:
        """Применение конкретной стратегии"""
        if strat_type == StrategyType.TREND_FOLLOWING:
            return await self._trend_following_strategy(ticker, data, params)
        elif strat_type == StrategyType.MEAN_REVERSION:
            return await self._mean_reversion_strategy(ticker, data, params)
        elif strat_type == StrategyType.BREAKOUT:
            return await self._breakout_strategy(ticker, data, params)
        elif strat_type == StrategyType.SCALPING:
            return await self._scalping_strategy(ticker, data, params)
        return []

    async def _trend_following_strategy(self, 
                                      ticker: str, 
                                      data: pd.DataFrame,
                                      params: Dict) -> List[TradeSignal]:
        """Трендовая стратегия на основе EMA и MACD"""
        if len(data) < 50:
            return []

        signals = []
        close_prices = data['close']
        
        # Расчет индикаторов
        ema_fast = talib.EMA(close_prices, timeperiod=params.get('ema_fast', 12))
        ema_slow = talib.EMA(close_prices, timeperiod=params.get('ema_slow', 26))
        macd, signal, _ = talib.MACD(close_prices, 
                                    fastperiod=12, 
                                    slowperiod=26, 
                                    signalperiod=9)

        last_close = close_prices.iloc[-1]
        current_time = datetime.now()

        # Генерация сигналов
        if ema_fast.iloc[-1] > ema_slow.iloc[-1] and macd.iloc[-1] > signal.iloc[-1]:
            sl_pct = params.get('sl_pct', 0.02)
            tp_pct = params.get('tp_pct', 0.04)
            
            signals.append(TradeSignal(
                ticker=ticker,
                signal_type=SignalType.ENTRY_LONG,
                price=last_close,
                timestamp=current_time,
                confidence=0.7,
                stop_loss=last_close * (1 - sl_pct),
                take_profit=last_close * (1 + tp_pct),
                strategy=StrategyType.TREND_FOLLOWING,
                metadata={
                    'ema_diff': ema_fast.iloc[-1] - ema_slow.iloc[-1],
                    'macd_diff': macd.iloc[-1] - signal.iloc[-1]
                }
            ))

        return signals

    async def _confirm_signals(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Проверка сигналов по дополнительным критериям"""
        confirmed = []
        min_conf = self.confirmation_rules['min_confidence']
        
        for signal in signals:
            if signal.confidence < min_conf:
                continue
                
            if self.confirmation_rules['volume_confirmation']:
                if not await self._volume_confirmation(signal):
                    continue
            
            if self.confirmation_rules['multi_timeframe']:
                if not await self._multi_timeframe_confirmation(signal):
                    continue
            
            confirmed.append(signal)
        
        return confirmed

    def _filter_signals(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Фильтрация и ранжирование сигналов"""
        if not signals:
            return []

        # Группировка и выбор лучшего сигнала для каждого типа
        filtered = []
        signals_by_type = {}
        
        for signal in signals:
            key = (signal.ticker, signal.signal_type)
            if key not in signals_by_type:
                signals_by_type[key] = []
            signals_by_type[key].append(signal)

        for sig_list in signals_by_type.values():
            best_signal = max(sig_list, key=lambda x: x.confidence)
            filtered.append(best_signal)

        return sorted(filtered, key=lambda x: x.confidence, reverse=True)

    async def backtest(self, 
                     strategy_type: StrategyType,
                     ticker: str,
                     timeframe: str,
                     start: datetime,
                     end: datetime) -> Dict:
        """Бэктестирование стратегии на исторических данных"""
        ohlcv = await self.data_handler.get_historical_data(
            ticker, timeframe, start, end
        )
        
        if ohlcv.empty:
            return {'error': 'No data available'}

        signals = await self._apply_strategy(
            strategy_type, ticker, ohlcv, {}
        )
        
        return self._analyze_backtest(signals, ohlcv)

    def _analyze_backtest(self,
                        signals: List[TradeSignal],
                        data: pd.DataFrame) -> Dict:
        """Анализ результатов бэктеста"""
        # Здесь должна быть более сложная логика анализа
        return {
            'total_signals': len(signals),
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0
        }

    # Заглушки для других стратегий (реализуйте по аналогии)
    async def _mean_reversion_strategy(self, ticker, data, params):
        return []

    async def _breakout_strategy(self, ticker, data, params):
        return []

    async def _scalping_strategy(self, ticker, data, params):
        return []

    async def _volume_confirmation(self, signal):
        """Подтверждение сигнала объемом"""
        return True

    async def _multi_timeframe_confirmation(self, signal):
        """Подтверждение на старшем таймфрейме"""
        return True