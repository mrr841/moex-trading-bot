import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
import logging
from scipy.stats import linregress

logger = logging.getLogger(__name__)

def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14
) -> pd.Series:
    """
    Расчет Average Directional Index (ADX)
    """
    try:
        adx = talib.ADX(high, low, close, timeperiod=window)
        return pd.Series(adx, index=close.index)
    except Exception as e:
        logger.error(f"ADX calculation error: {str(e)}")
        return pd.Series(np.nan, index=close.index)

def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14
) -> pd.Series:
    """
    Расчет Average True Range (ATR)
    """
    try:
        atr = talib.ATR(high, low, close, timeperiod=window)
        return pd.Series(atr, index=close.index)
    except Exception as e:
        logger.error(f"ATR calculation error: {str(e)}")
        return pd.Series(np.nan, index=close.index)

def calculate_ema(
    prices: pd.Series,
    window: int,
    adjust: bool = False
) -> pd.Series:
    """
    Расчет Exponential Moving Average (EMA)
    """
    try:
        return prices.ewm(span=window, adjust=adjust).mean()
    except Exception as e:
        logger.error(f"EMA calculation error: {str(e)}")
        return pd.Series(np.nan, index=prices.index)

def calculate_rsi(
    prices: pd.Series,
    window: int = 14
) -> pd.Series:
    """
    Расчет Relative Strength Index (RSI)
    """
    try:
        rsi = talib.RSI(prices, timeperiod=window)
        return pd.Series(rsi, index=prices.index)
    except Exception as e:
        logger.error(f"RSI calculation error: {str(e)}")
        return pd.Series(np.nan, index=prices.index)

def calculate_bollinger_bands(
    prices: pd.Series,
    window: int = 20,
    num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Расчет Bollinger Bands
    """
    try:
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return upper_band, sma, lower_band
    except Exception as e:
        logger.error(f"Bollinger Bands calculation error: {str(e)}")
        return (
            pd.Series(np.nan, index=prices.index),
            pd.Series(np.nan, index=prices.index),
            pd.Series(np.nan, index=prices.index)
        )

def calculate_volume_profile(
    prices: pd.Series,
    volumes: pd.Series,
    bins: int = 20
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Расчет Volume Profile
    """
    try:
        hist, bin_edges = np.histogram(
            prices,
            bins=bins,
            weights=volumes
        )
        return bin_edges[:-1], hist
    except Exception as e:
        logger.error(f"Volume Profile calculation error: {str(e)}")
        return np.array([]), np.array([])

def calculate_macd(
    prices: pd.Series,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Расчет MACD (Moving Average Convergence Divergence)
    """
    try:
        macd, signal, hist = talib.MACD(
            prices,
            fastperiod=fast_window,
            slowperiod=slow_window,
            signalperiod=signal_window
        )
        return (
            pd.Series(macd, index=prices.index),
            pd.Series(signal, index=prices.index),
            pd.Series(hist, index=prices.index)
        )
    except Exception as e:
        logger.error(f"MACD calculation error: {str(e)}")
        return (
            pd.Series(np.nan, index=prices.index),
            pd.Series(np.nan, index=prices.index),
            pd.Series(np.nan, index=prices.index)
        )

def calculate_support_resistance(
    prices: pd.Series,
    window: int = 50,
    tolerance: float = 0.01
) -> Tuple[Optional[float], Optional[float]]:
    """
    Расчет уровней поддержки и сопротивления
    """
    try:
        if len(prices) < window:
            return None, None
            
        rolling_min = prices.rolling(window=window).min()
        rolling_max = prices.rolling(window=window).max()
        
        support = rolling_min.iloc[-1]
        resistance = rolling_max.iloc[-1]
        
        recent_prices = prices.iloc[-window:]
        support_candidates = recent_prices[recent_prices <= support * (1 + tolerance)]
        resistance_candidates = recent_prices[recent_prices >= resistance * (1 - tolerance)]
        
        support = support_candidates.mean() if not support_candidates.empty else None
        resistance = resistance_candidates.mean() if not resistance_candidates.empty else None
        
        return support, resistance
    except Exception as e:
        logger.error(f"Support/Resistance calculation error: {str(e)}")
        return None, None

def calculate_sma(
    prices: pd.Series,
    window: int
) -> pd.Series:
    """
    Расчет Simple Moving Average (SMA)
    
    Args:
        prices: Временной ряд цен
        window: Период расчета
    
    Returns:
        pd.Series: Значения SMA
    """
    try:
        sma = prices.rolling(window=window).mean()
        return sma
    except Exception as e:
        logger.error(f"SMA calculation error: {str(e)}")
        return pd.Series(np.nan, index=prices.index)
