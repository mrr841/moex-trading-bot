import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta, time
from functools import wraps
import pytz
import pandas as pd
import numpy as np
from pathlib import Path
import json
import inspect
import hashlib
import re

logger = logging.getLogger(__name__)

def async_retry(max_retries: int = 3, delay: float = 1.0, exceptions=(Exception,)):
    """
    Декоратор для повторного выполнения асинхронных функций при ошибках
    
    Args:
        max_retries: Максимальное количество попыток
        delay: Задержка между попытками (в секундах)
        exceptions: Кортеж исключений для перехвата
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return await f(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {f.__name__}")
                        raise
                    
                    wait = delay * attempt
                    logger.warning(f"Retry {attempt}/{max_retries} for {f.__name__} after {wait} sec. Error: {str(e)}")
                    await asyncio.sleep(wait)
        return wrapper
    return decorator

def calculate_pnl(entry_price: float, exit_price: float, quantity: int, fees: float = 0.0) -> Dict[str, float]:
    """
    Расчет прибыли/убытка по сделке
    
    Args:
        entry_price: Цена входа
        exit_price: Цена выхода
        quantity: Количество
        fees: Комиссии (абсолютное значение)
        
    Returns:
        Dict: {'gross': общий PnL, 'net': PnL после комиссий, 'percent': процент дохода}
    """
    gross_pnl = (exit_price - entry_price) * quantity
    net_pnl = gross_pnl - fees
    pct_pnl = (exit_price / entry_price - 1) * 100 if entry_price != 0 else 0
    
    return {
        'gross': round(gross_pnl, 2),
        'net': round(net_pnl, 2),
        'percent': round(pct_pnl, 2)
    }

def format_price(price: float, ticker: Optional[str] = None) -> str:
    """
    Форматирование цены в зависимости от инструмента
    
    Args:
        price: Цена для форматирования
        ticker: Тикер инструмента (опционально)
        
    Returns:
        str: Отформатированная строка цены
    """
    if ticker and ticker.endswith('USD'):
        return f"${price:,.2f}"
    return f"{price:,.2f} ₽"

def parse_timedelta(time_str: str) -> timedelta:
    """
    Парсинг строки временного интервала в timedelta
    
    Поддерживаемые форматы:
    - '1h' -> 1 час
    - '30m' -> 30 минут
    - '1d' -> 1 день
    
    Args:
        time_str: Строка временного интервала
        
    Returns:
        timedelta: Объект временного интервала
    """
    units = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks'
    }
    
    match = re.match(r'^(\d+)([smhdw])$', time_str.lower())
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
    
    value, unit = match.groups()
    return timedelta(**{units[unit]: int(value)})

def validate_config(config: Dict, required_keys: List[str]) -> bool:
    """
    Валидация конфигурационного файла
    
    Args:
        config: Словарь конфигурации
        required_keys: Список обязательных ключей
        
    Returns:
        bool: True если конфиг валиден
    """
    missing = [key for key in required_keys if key not in config]
    if missing:
        logger.error(f"Missing required config keys: {missing}")
        return False
    return True

def time_in_range(start: time, end: time, current: Optional[datetime] = None) -> bool:
    """
    Проверка, находится ли текущее время в заданном диапазоне
    
    Args:
        start: Начальное время
        end: Конечное время
        current: Текущее время (опционально)
        
    Returns:
        bool: True если текущее время в диапазоне
    """
    now = current or datetime.now(pytz.UTC)
    current_time = now.time()
    
    if start <= end:
        return start <= current_time <= end
    else:  # Переход через полночь
        return current_time >= start or current_time <= end

def generate_unique_id(data: Any) -> str:
    """
    Генерация уникального ID на основе входных данных
    
    Args:
        data: Данные для хеширования
        
    Returns:
        str: Уникальный хеш-идентификатор
    """
    data_str = str(data).encode('utf-8')
    return hashlib.md5(data_str).hexdigest()[:8]

def dataframe_to_dict(df: pd.DataFrame) -> Dict:
    """
    Конвертация DataFrame в словарь с сохранением типов
    
    Args:
        df: Входной DataFrame
        
    Returns:
        Dict: Словарь с данными
    """
    return {
        'columns': list(df.columns),
        'data': json.loads(df.to_json(orient='records', date_format='iso')),
        'index': list(df.index.astype(str))
    }

def dict_to_dataframe(data: Dict) -> pd.DataFrame:
    """
    Конвертация словаря обратно в DataFrame
    
    Args:
        data: Словарь с данными
        
    Returns:
        pd.DataFrame: Восстановленный DataFrame
    """
    df = pd.DataFrame(data['data'])
    if 'index' in data and len(data['index']) == len(df):
        df.index = pd.to_datetime(data['index'])
    return df

def get_market_hours(exchange: str = 'MOEX') -> Tuple[time, time]:
    """
    Получение времени работы биржи
    
    Args:
        exchange: Название биржи (MOEX, NYSE и т.д.)
        
    Returns:
        Tuple: (open_time, close_time)
    """
    markets = {
        'MOEX': (time(9, 50), time(18, 40)),
        'NYSE': (time(9, 30), time(16, 0))
    }
    return markets.get(exchange, (time(0, 0), time(23, 59)))

def calculate_position_size(balance: float, 
                          risk_pct: float, 
                          entry_price: float, 
                          stop_loss: float) -> int:
    """
    Расчет размера позиции на основе риска
    
    Args:
        balance: Торговый баланс
        risk_pct: Риск в процентах от баланса
        entry_price: Цена входа
        stop_loss: Цена стоп-лосса
        
    Returns:
        int: Размер позиции (количество)
    """
    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share == 0:
        return 0
    risk_amount = balance * risk_pct / 100
    return int(risk_amount / risk_per_share)

def normalize_ticker(ticker: str) -> str:
    """
    Нормализация тикера (приведение к стандартному формату)
    
    Args:
        ticker: Входной тикер
        
    Returns:
        str: Нормализованный тикер
    """
    return ticker.strip().upper()

def log_execution_time(func):
    """
    Декоратор для логирования времени выполнения функций
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = datetime.now()
        result = await func(*args, **kwargs)
        duration = (datetime.now() - start).total_seconds()
        logger.debug(f"Function {func.__name__} executed in {duration:.3f} sec")
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = datetime.now()
        result = func(*args, **kwargs)
        duration = (datetime.now() - start).total_seconds()
        logger.debug(f"Function {func.__name__} executed in {duration:.3f} sec")
        return result

    return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

def split_list(items: List[Any], n: int) -> List[List[Any]]:
    """
    Разделение списка на N примерно равных частей
    
    Args:
        items: Входной список
        n: Количество частей
        
    Returns:
        List[List]: Разделенный список
    """
    k, m = divmod(len(items), n)
    return [items[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]