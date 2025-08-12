import numpy as np
import pandas as pd
from typing import Optional, Tuple, List
import logging
from scipy.stats import linregress
from numba import njit  # Для ускорения вычислений

logger = logging.getLogger(__name__)

@njit
def _rolling_fractal(high: np.ndarray, low: np.ndarray, window: int) -> Tuple[np.ndarray, np.ndarray]:
    """Вычисление фракталов (внутренняя функция с Numba)"""
    n = len(high)
    up_fractals = np.zeros(n)
    down_fractals = np.zeros(n)
    
    for i in range(window, n-window):
        # Проверка верхнего фрактала
        is_up = True
        for j in range(i-window, i+window+1):
            if j == i:
                continue
            if high[i] < high[j]:
                is_up = False
                break
        up_fractals[i] = 1 if is_up else 0
        
        # Проверка нижнего фрактала
        is_down = True
        for j in range(i-window, i+window+1):
            if j == i:
                continue
            if low[i] > low[j]:
                is_down = False
                break
        down_fractals[i] = 1 if is_down else 0
        
    return up_fractals, down_fractals

def fractal_breakout_detector(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 5,
    threshold: float = 0.01
) -> pd.Series:
    """
    Детектор фрактальных пробоев (на основе Bill Williams Fractals)
    
    Args:
        high: Цена high
        low: Цена low
        close: Цена close
        window: Размер окна для поиска фракталов
        threshold: Минимальный размер пробоя в %
        
    Returns:
        pd.Series: 1 - пробой вверх, -1 - пробой вниз, 0 - нет сигнала
    """
    try:
        h = high.values
        l = low.values
        c = close.values
        
        up_frac, down_frac = _rolling_fractal(h, l, window)
        
        signals = np.zeros(len(c))
        for i in range(1, len(c)):
            # Проверка пробоя верхнего фрактала
            if up_frac[i-1] == 1 and c[i] > h[i-1] * (1 + threshold):
                signals[i] = 1
            # Проверка пробоя нижнего фрактала
            elif down_frac[i-1] == 1 and c[i] < l[i-1] * (1 - threshold):
                signals[i] = -1
                
        return pd.Series(signals, index=close.index)
    except Exception as e:
        logger.error(f"Fractal breakout detector error: {str(e)}")
        return pd.Series(np.zeros(len(close)), index=close.index)

def volume_spike_detector(
    volume: pd.Series,
    window: int = 20,
    multiplier: float = 2.5
) -> pd.Series:
    """
    Детектор аномальных объемов (спайков)
    
    Args:
        volume: Временной ряд объемов
        window: Размер окна для расчета среднего
        multiplier: Множитель стандартного отклонения
        
    Returns:
        pd.Series: 1 - спайк объема, 0 - нет спайка
    """
    try:
        rolling_mean = volume.rolling(window=window).mean()
        rolling_std = volume.rolling(window=window).std()
        threshold = rolling_mean + multiplier * rolling_std
        
        spikes = (volume > threshold).astype(int)
        return spikes
    except Exception as e:
        logger.error(f"Volume spike detector error: {str(e)}")
        return pd.Series(np.zeros(len(volume)), index=volume.index)

def trend_intensity_index(
    prices: pd.Series,
    volume: pd.Series,
    window: int = 14
) -> pd.Series:
    """
    Индекс интенсивности тренда (объем-взвешенный)
    
    Args:
        prices: Временной ряд цен
        volume: Временной ряд объемов
        window: Размер окна расчета
        
    Returns:
        pd.Series: Значения индекса (0-100)
    """
    try:
        returns = prices.pct_change()
        volume_weighted = returns * volume
        rolling_sum = volume_weighted.rolling(window).sum()
        rolling_abs_sum = (volume_weighted.abs()).rolling(window).sum()
        
        tii = 100 * rolling_sum / rolling_abs_sum
        return tii.fillna(0)
    except Exception as e:
        logger.error(f"Trend intensity index error: {str(e)}")
        return pd.Series(np.zeros(len(prices)), index=prices.index)

def anchored_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    anchor_date: Optional[str] = None
) -> pd.Series:
    """
    Anchored VWAP (Volume Weighted Average Price) от определенной даты
    
    Args:
        high: Цена high
        low: Цена low
        close: Цена close
        volume: Объемы
        anchor_date: Дата якоря (None - с начала данных)
        
    Returns:
        pd.Series: Значения VWAP
    """
    try:
        typical_price = (high + low + close) / 3
        if anchor_date:
            mask = (typical_price.index >= anchor_date)
            typical_price = typical_price[mask]
            volume = volume[mask]
        
        cum_vol_price = (typical_price * volume).cumsum()
        cum_vol = volume.cumsum()
        vwap = cum_vol_price / cum_vol
        return vwap
    except Exception as e:
        logger.error(f"Anchored VWAP error: {str(e)}")
        return pd.Series(np.zeros(len(close)), index=close.index)

def heikin_ashi_smoothed(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    smoothing_window: int = 3
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Модифицированные свечи Heikin Ashi со сглаживанием
    
    Args:
        open_: Цена open
        high: Цена high
        low: Цена low
        close: Цена close
        smoothing_window: Окно сглаживания
        
    Returns:
        Tuple: (ha_open, ha_high, ha_low, ha_close)
    """
    try:
        # Классические Heikin Ashi
        ha_close = (open_ + high + low + close) / 4
        ha_open = (open_.shift(1) + close.shift(1)) / 2
        ha_open.iloc[0] = open_.iloc[0]
        ha_high = pd.concat([high, ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([low, ha_open, ha_close], axis=1).min(axis=1)
        
        # Дополнительное сглаживание
        if smoothing_window > 1:
            ha_open = ha_open.rolling(smoothing_window).mean()
            ha_high = ha_high.rolling(smoothing_window).mean()
            ha_low = ha_low.rolling(smoothing_window).mean()
            ha_close = ha_close.rolling(smoothing_window).mean()
            
        return ha_open, ha_high, ha_low, ha_close
    except Exception as e:
        logger.error(f"Heikin Ashi smoothed error: {str(e)}")
        return (
            pd.Series(np.zeros(len(open_)), index=open_.index,
            pd.Series(np.zeros(len(high))), index=high.index,
            pd.Series(np.zeros(len(low))), index=low.index,
            pd.Series(np.zeros(len(close))), index=close.index
        )

def cumulative_delta(
    buy_volume: pd.Series,
    sell_volume: pd.Series,
    window: Optional[int] = None
) -> pd.Series:
    """
    Кумулятивная дельта (разница между объемом покупок и продаж)
    
    Args:
        buy_volume: Объемы на покупку
        sell_volume: Объемы на продажу
        window: Окно для скользящей дельты (None - кумулятивная сумма)
        
    Returns:
        pd.Series: Значения дельты
    """
    try:
        delta = buy_volume - sell_volume
        if window:
            return delta.rolling(window).sum()
        return delta.cumsum()
    except Exception as e:
        logger.error(f"Cumulative delta error: {str(e)}")
        return pd.Series(np.zeros(len(buy_volume)), index=buy_volume.index)