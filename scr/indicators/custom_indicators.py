import numpy as np
import pandas as pd
from typing import Optional, Tuple
import logging
from numba import njit

logger = logging.getLogger(__name__)

@njit
def _rolling_fractal(high: np.ndarray, low: np.ndarray, window: int) -> Tuple[np.ndarray, np.ndarray]:
    n = len(high)
    up_fractals = np.zeros(n, dtype=np.int8)
    down_fractals = np.zeros(n, dtype=np.int8)
    
    for i in range(window, n - window):
        is_up = True
        is_down = True
        for j in range(i - window, i + window + 1):
            if j == i:
                continue
            if high[i] < high[j]:
                is_up = False
            if low[i] > low[j]:
                is_down = False
            if not is_up and not is_down:
                break
        up_fractals[i] = 1 if is_up else 0
        down_fractals[i] = 1 if is_down else 0
        
    return up_fractals, down_fractals

def fractal_breakout_detector(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 5,
    threshold: float = 0.01
) -> pd.Series:
    try:
        h = high.values
        l = low.values
        c = close.values
        
        up_frac, down_frac = _rolling_fractal(h, l, window)
        
        signals = np.zeros(len(c), dtype=np.int8)
        for i in range(1, len(c)):
            if up_frac[i - 1] == 1 and c[i] > h[i - 1] * (1 + threshold):
                signals[i] = 1
            elif down_frac[i - 1] == 1 and c[i] < l[i - 1] * (1 - threshold):
                signals[i] = -1
                
        return pd.Series(signals, index=close.index)
    except Exception as e:
        logger.error(f"Fractal breakout detector error: {e}")
        return pd.Series(np.zeros(len(close), dtype=np.int8), index=close.index)

def volume_spike_detector(
    volume: pd.Series,
    window: int = 20,
    multiplier: float = 2.5
) -> pd.Series:
    try:
        rolling_mean = volume.rolling(window=window).mean()
        rolling_std = volume.rolling(window=window).std()
        threshold = rolling_mean + multiplier * rolling_std
        
        spikes = (volume > threshold).astype(np.int8)
        return spikes
    except Exception as e:
        logger.error(f"Volume spike detector error: {e}")
        return pd.Series(np.zeros(len(volume), dtype=np.int8), index=volume.index)

def trend_intensity_index(
    prices: pd.Series,
    volume: pd.Series,
    window: int = 14
) -> pd.Series:
    try:
        returns = prices.pct_change()
        volume_weighted = returns * volume
        rolling_sum = volume_weighted.rolling(window).sum()
        rolling_abs_sum = volume_weighted.abs().rolling(window).sum()
        
        tii = 100 * rolling_sum / rolling_abs_sum
        return tii.fillna(0)
    except Exception as e:
        logger.error(f"Trend intensity index error: {e}")
        return pd.Series(np.zeros(len(prices)), index=prices.index)

def anchored_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    anchor_date: Optional[str] = None
) -> pd.Series:
    try:
        typical_price = (high + low + close) / 3
        if anchor_date:
            mask = typical_price.index >= anchor_date
            typical_price = typical_price.loc[mask]
            volume = volume.loc[mask]
        
        cum_vol_price = (typical_price * volume).cumsum()
        cum_vol = volume.cumsum()
        vwap = cum_vol_price / cum_vol
        
        vwap = vwap.reindex(close.index).ffill().bfill()
        return vwap
    except Exception as e:
        logger.error(f"Anchored VWAP error: {e}")
        return pd.Series(np.zeros(len(close)), index=close.index)

def heikin_ashi_smoothed(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    smoothing_window: int = 3
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    try:
        ha_close = (open_ + high + low + close) / 4
        ha_open = (open_.shift(1) + close.shift(1)) / 2
        ha_open.iloc[0] = open_.iloc[0]
        ha_high = pd.concat([high, ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([low, ha_open, ha_close], axis=1).min(axis=1)
        
        if smoothing_window > 1:
            ha_open = ha_open.rolling(smoothing_window).mean()
            ha_high = ha_high.rolling(smoothing_window).mean()
            ha_low = ha_low.rolling(smoothing_window).mean()
            ha_close = ha_close.rolling(smoothing_window).mean()
            
        return ha_open, ha_high, ha_low, ha_close
    except Exception as e:
        logger.error(f"Heikin Ashi smoothed error: {e}")
        length = len(open_)
        zero_series = pd.Series(np.zeros(length), index=open_.index)
        return zero_series, zero_series, zero_series, zero_series

def cumulative_delta(
    buy_volume: pd.Series,
    sell_volume: pd.Series,
    window: Optional[int] = None
) -> pd.Series:
    try:
        delta = buy_volume - sell_volume
        if window is not None and window > 0:
            return delta.rolling(window).sum()
        return delta.cumsum()
    except Exception as e:
        logger.error(f"Cumulative delta error: {e}")
        return pd.Series(np.zeros(len(buy_volume)), index=buy_volume.index)


# --- Добавленные функции ---

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

def detect_liquidity_regime(
    volume: pd.Series,
    window: int = 20,
    threshold_multiplier: float = 1.5
) -> pd.Series:
    """
    Классификация режима ликвидности на основе объёма.
    Возвращает:
      1 — высокая ликвидность,
      0 — нормальная,
     -1 — низкая ликвидность
    """
    try:
        rolling_mean = volume.rolling(window).mean()
        rolling_std = volume.rolling(window).std()
        high_thresh = rolling_mean + threshold_multiplier * rolling_std
        low_thresh = rolling_mean - threshold_multiplier * rolling_std

        regime = pd.Series(0, index=volume.index)
        regime[volume > high_thresh] = 1
        regime[volume < low_thresh] = -1
        return regime.fillna(0)
    except Exception as e:
        logger.error(f"Detect liquidity regime error: {e}")
        return pd.Series(np.zeros(len(volume)), index=volume.index)

def detect_volatility_regime(
    close: pd.Series,
    window: int = 20,
    threshold_multiplier: float = 1.5
) -> pd.Series:
    """
    Классификация режима волатильности по стандартному отклонению доходностей.
    Возвращает:
      1 — высокая волатильность,
      0 — нормальная,
     -1 — низкая волатильность
    """
    try:
        returns = close.pct_change()
        rolling_std = returns.rolling(window).std()
        mean_std = rolling_std.rolling(window).mean()
        
        high_thresh = mean_std * threshold_multiplier
        low_thresh = mean_std / threshold_multiplier
        
        regime = pd.Series(0, index=close.index)
        regime[rolling_std > high_thresh] = 1
        regime[rolling_std < low_thresh] = -1
        return regime.fillna(0)
    except Exception as e:
        logger.error(f"Detect volatility regime error: {e}")
        return pd.Series(np.zeros(len(close)), index=close.index)
