import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
import logging
from enum import Enum, auto
from dataclasses import dataclass
import talib
from scipy.stats import linregress
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)


def detect_trend(
    close: pd.Series,
    short_window: int = 12,
    long_window: int = 26
) -> pd.Series:
    """
    Простая детекция тренда по пересечению скользящих средних.
    Возвращает:
      1 — восходящий тренд,
     -1 — нисходящий тренд,
      0 — без тренда
    """
    try:
        short_ma = close.rolling(short_window).mean()
        long_ma = close.rolling(long_window).mean()
        trend = pd.Series(0, index=close.index)

        trend[(short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))] = 1
        trend[(short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))] = -1

        # Заполняем зоны тренда
        current_trend = 0
        for i in range(len(trend)):
            if trend.iat[i] != 0:
                current_trend = trend.iat[i]
            else:
                trend.iat[i] = current_trend
        return trend
    except Exception as e:
        logger.error(f"Detect trend error: {e}")
        return pd.Series(np.zeros(len(close)), index=close.index)


def detect_volatility_regime(
    volatility: float,
    low_threshold: float = 0.005,
    high_threshold: float = 0.02
) -> 'MarketRegime':
    """Определение режима волатильности по порогам"""
    if volatility > high_threshold:
        return MarketRegime.HIGH_VOLATILITY
    elif volatility < low_threshold:
        return MarketRegime.LOW_VOLATILITY
    else:
        return MarketRegime.SIDEWAYS


def detect_liquidity_regime(
    liquidity_ratio: float,
    low_threshold: float = 0.5,
    high_threshold: float = 1.5
) -> 'MarketRegime':
    """Определение режима ликвидности по порогам"""
    if liquidity_ratio > high_threshold:
        return MarketRegime.LIQUID
    elif liquidity_ratio < low_threshold:
        return MarketRegime.ILLIQUID
    else:
        return MarketRegime.SIDEWAYS


class MarketRegime(Enum):
    TREND_UP = auto()
    TREND_DOWN = auto()
    SIDEWAYS = auto()
    HIGH_VOLATILITY = auto()
    LOW_VOLATILITY = auto()
    LIQUID = auto()
    ILLIQUID = auto()


@dataclass
class RegimeDetectionResult:
    primary_regime: MarketRegime
    secondary_regimes: List[MarketRegime]
    confidence: float
    indicators: Dict[str, float]


class MarketRegimeDetector:
    """Определитель рыночных режимов на основе мультимодального анализа"""

    def __init__(self, config: Dict):
        self.config = config
        self.volatility_window = config.get('volatility_window', 14)
        self.trend_window = config.get('trend_window', 21)
        self.liquidity_threshold = config.get('liquidity_threshold', 1_000_000)
        self.volatility_thresholds = {
            'low': config.get('volatility_low_threshold', 0.005),
            'high': config.get('volatility_high_threshold', 0.02)
        }

    async def detect_regime(self,
                            ticker: str,
                            data_handler,
                            timeframe: str) -> RegimeDetectionResult:
        """
        Основной метод определения текущего рыночного режима

        Args:
            ticker: Тикер инструмента
            data_handler: Обработчик данных
            timeframe: Таймфрейм для анализа

        Returns:
            RegimeDetectionResult: Результат детекции режима
        """
        # Получение необходимых данных
        ohlcv = await data_handler.get_ohlcv(ticker, timeframe)
        if ohlcv.empty:
            raise ValueError(f"No data available for {ticker} {timeframe}")

        # Вычисление ключевых показателей
        volatility = self._calculate_volatility(ohlcv)
        trend_strength, trend_direction = self._assess_trend(ohlcv)
        liquidity = self._assess_liquidity(ohlcv)
        mean_reversion = self._check_mean_reversion(ohlcv)

        # Определение основного режима
        primary_regime, primary_confidence = self._determine_primary_regime(
            trend_strength,
            trend_direction,
            volatility
        )

        # Определение дополнительных режимов
        secondary_regimes = self._determine_secondary_regimes(
            volatility,
            liquidity,
            mean_reversion
        )

        # Формирование результата
        indicators = {
            'volatility': volatility,
            'trend_strength': trend_strength,
            'trend_direction': trend_direction,
            'liquidity': liquidity,
            'mean_reversion_score': mean_reversion
        }

        return RegimeDetectionResult(
            primary_regime=primary_regime,
            secondary_regimes=secondary_regimes,
            confidence=primary_confidence,
            indicators=indicators
        )

    def _calculate_volatility(self, ohlcv: pd.DataFrame) -> float:
        """Расчет волатильности на основе ATR"""
        atr = talib.ATR(
            ohlcv['high'],
            ohlcv['low'],
            ohlcv['close'],
            timeperiod=self.volatility_window
        )
        return atr.iloc[-1] / ohlcv['close'].iloc[-1]

    def _assess_trend(self, ohlcv: pd.DataFrame) -> Tuple[float, float]:
        """Оценка силы и направления тренда"""
        # ADX для силы тренда
        adx = talib.ADX(
            ohlcv['high'],
            ohlcv['low'],
            ohlcv['close'],
            timeperiod=self.trend_window
        )

        # Наклон регрессии для направления
        prices = ohlcv['close'].values[-self.trend_window:]
        x = np.arange(len(prices))
        slope, _, _, _, _ = linregress(x, prices)

        trend_strength = adx.iloc[-1] / 100  # Нормализация 0-1
        trend_direction = np.sign(slope)

        return trend_strength, trend_direction

    def _assess_liquidity(self, ohlcv: pd.DataFrame) -> float:
        """Оценка ликвидности на основе объема"""
        avg_volume = ohlcv['volume'].rolling(self.trend_window).mean().iloc[-1]
        return avg_volume / self.liquidity_threshold

    def _check_mean_reversion(self, ohlcv: pd.DataFrame) -> float:
        """Проверка свойства возврата к среднему (ADF тест)"""
        prices = ohlcv['close'].values
        result = adfuller(prices)
        return result[1]  # p-value

    def _determine_primary_regime(self,
                                 trend_strength: float,
                                 trend_direction: float,
                                 volatility: float) -> Tuple[MarketRegime, float]:
        """Определение основного рыночного режима"""
        # Определение трендового режима
        if trend_strength > 0.5:  # Сильный тренд
            if trend_direction > 0:
                return MarketRegime.TREND_UP, trend_strength
            else:
                return MarketRegime.TREND_DOWN, trend_strength

        # Определение волатильности
        if volatility > self.volatility_thresholds['high']:
            return MarketRegime.HIGH_VOLATILITY, 0.8
        elif volatility < self.volatility_thresholds['low']:
            return MarketRegime.LOW_VOLATILITY, 0.8

        # Дефолтный режим - боковик
        return MarketRegime.SIDEWAYS, 0.7

    def _determine_secondary_regimes(self,
                                    volatility: float,
                                    liquidity: float,
                                    mean_reversion: float) -> List[MarketRegime]:
        """Определение дополнительных режимов"""
        regimes = []

        # Режим ликвидности
        regime_liquidity = detect_liquidity_regime(liquidity)
        if regime_liquidity != MarketRegime.SIDEWAYS:
            regimes.append(regime_liquidity)

        # Дополнительные проверки волатильности
        regime_volatility = detect_volatility_regime(volatility)
        if regime_volatility != MarketRegime.SIDEWAYS:
            regimes.append(regime_volatility)

        return regimes

    async def detect_regime_multi_timeframe(self,
                                           ticker: str,
                                           data_handler,
                                           timeframes: List[str]) -> Dict[str, RegimeDetectionResult]:
        """Анализ режимов на нескольких таймфреймах"""
        results = {}
        for tf in timeframes:
            try:
                results[tf] = await self.detect_regime(ticker, data_handler, tf)
            except Exception as e:
                logger.error(f"Regime detection failed for {ticker} {tf}: {str(e)}")
                continue
        return results

    def get_strategy_recommendations(self,
                                     regime_result: RegimeDetectionResult) -> List[str]:
        """Рекомендации стратегий на основе режима"""
        recs = []

        if regime_result.primary_regime in [MarketRegime.TREND_UP, MarketRegime.TREND_DOWN]:
            recs.append("TrendFollowingStrategy")
            if regime_result.indicators['volatility'] > self.volatility_thresholds['high']:
                recs.append("BreakoutStrategy")

        elif regime_result.primary_regime == MarketRegime.SIDEWAYS:
            recs.append("MeanReversionStrategy")
            if MarketRegime.LOW_VOLATILITY in regime_result.secondary_regimes:
                recs.append("ScalpingStrategy")

        if MarketRegime.HIGH_VOLATILITY in regime_result.secondary_regimes:
            recs.append("ReducePositionSizing")

        if MarketRegime.ILLIQUID in regime_result.secondary_regimes:
            recs.append("AvoidTrading")

        return recs
