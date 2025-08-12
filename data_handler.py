import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging
import cachetools
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные окружения

class DataHandler:
    """Обработчик данных для MOEX и Tinkoff API"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger('data_handler')
        self.cache = cachetools.TTLCache(maxsize=100, ttl=3600)
        self.session = None
        self.data_path = Path(config.get('data_path', 'data/'))
        self.data_path.mkdir(exist_ok=True)
        self._init_api_settings()

    def _init_api_settings(self):
        """Инициализация настроек API из конфига и переменных окружения"""
        self.api_mode = self.config['mode']  # paper/real
        self.tinkoff_token = os.getenv(
            'TINKOFF_REAL_TOKEN' if self.api_mode == 'real' else 'TINKOFF_SANDBOX_TOKEN'
        )
        self.account_id = os.getenv('TINKOFF_ACCOUNT_ID')
        self.moex_timeout = int(os.getenv('MOEX_API_TIMEOUT', 10))

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.moex_timeout))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def _fetch(self, url: str, params: dict = None) -> dict:
        """Базовый метод для HTTP-запросов"""
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            self.logger.error(f"Request failed: {url} - {str(e)}")
            raise

    # MOEX ISS API методы
    async def fetch_moex_candles(
        self, 
        ticker: str, 
        timeframe: str, 
        from_date: str, 
        to_date: str
    ) -> pd.DataFrame:
        """Получение исторических данных с MOEX ISS"""
        cache_key = f"moex_{ticker}_{timeframe}_{from_date}_{to_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        url = f"{self.config['api_settings']['moex']['base_url']}/engines/stock/markets/shares/securities/{ticker}/candles.json"
        params = {
            'from': from_date,
            'till': to_date,
            'interval': self._convert_timeframe(timeframe),
            'start': 0
        }

        data = await self._fetch(url, params)
        df = pd.DataFrame(data['candles']['data'], columns=data['candles']['columns'])
        df['begin'] = pd.to_datetime(df['begin'])
        df.set_index('begin', inplace=True)

        self.cache[cache_key] = df
        return df

    # Tinkoff API методы
    async def fetch_tinkoff_candles(
        self,
        ticker: str,
        timeframe: str,
        days_back: int = 30
    ) -> pd.DataFrame:
        """Получение свечей с Tinkoff API"""
        from tinkoff.invest import (
            AsyncClient,
            CandleInterval,
            HistoricCandle
        )

        tf_mapping = {
            '1m': CandleInterval.CANDLE_INTERVAL_1_MIN,
            '5m': CandleInterval.CANDLE_INTERVAL_5_MIN,
            '1h': CandleInterval.CANDLE_INTERVAL_HOUR,
            '1d': CandleInterval.CANDLE_INTERVAL_DAY
        }

        async with AsyncClient(self.tinkoff_token) as client:
            resp = await client.get_all_candles(
                figi=await self._get_figi(ticker),
                from_=datetime.utcnow() - timedelta(days=days_back),
                interval=tf_mapping[timeframe]
            )

            candles = []
            for candle in resp:
                candles.append({
                    'open': self._quotation_to_float(candle.open),
                    'high': self._quotation_to_float(candle.high),
                    'low': self._quotation_to_float(candle.low),
                    'close': self._quotation_to_float(candle.close),
                    'volume': candle.volume,
                    'time': candle.time
                })

            df = pd.DataFrame(candles)
            df.set_index('time', inplace=True)
            return df

    # Вспомогательные методы
    def _convert_timeframe(self, timeframe: str) -> int:
        """Конвертация таймфрейма для MOEX ISS API"""
        tf_map = {
            '1m': 1,
            '5m': 5,
            '10m': 10,
            '1h': 60,
            '1d': 24
        }
        return tf_map.get(timeframe, 1)

    async def _get_figi(self, ticker: str) -> str:
        """Получение FIGI по тикеру"""
        cache_key = f"figi_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        from tinkoff.invest import AsyncClient
        async with AsyncClient(self.tinkoff_token) as client:
            resp = await client.instruments.shares()
            for share in resp.instruments:
                if share.ticker == ticker:
                    self.cache[cache_key] = share.figi
                    return share.figi

        raise ValueError(f"FIGI not found for {ticker}")

    @staticmethod
    def _quotation_to_float(q) -> float:
        """Конвертация Quotation в float"""
        return q.units + q.nano / 1e9

    # Методы для работы с ордерами
    async def get_orderbook(self, ticker: str, depth: int = 10) -> dict:
        """Получение стакана"""
        if self.config['api_source'].startswith('tinkoff'):
            from tinkoff.invest import AsyncClient
            async with AsyncClient(self.tinkoff_token) as client:
                resp = await client.get_order_book(
                    figi=await self._get_figi(ticker),
                    depth=depth
                )
                return {
                    'bids': [(self._quotation_to_float(b.price), b.quantity) for b in resp.bids],
                    'asks': [(self._quotation_to_float(a.price), a.quantity) for a in resp.asks]
                }
        else:
            url = f"{self.config['api_settings']['moex']['base_url']}/engines/stock/markets/shares/securities/{ticker}/orderbook.json"
            data = await self._fetch(url)
            return {
                'bids': [(float(b[0]), int(b[1])) for b in data['orderbook']['data']['bids']],
                'asks': [(float(a[0]), int(a[1])) for a in data['orderbook']['data']['asks']]
            }

    # Кеширование данных
    async def save_to_cache(self, ticker: str, data: pd.DataFrame, data_type: str):
        """Сохранение данных в локальный кеш"""
        cache_file = self.data_path / f"{ticker}_{data_type}.parquet"
        data.to_parquet(cache_file)
        self.logger.info(f"Saved {ticker} {data_type} data to cache")

    async def load_from_cache(self, ticker: str, data_type: str) -> Optional[pd.DataFrame]:
        """Загрузка данных из локального кеша"""
        cache_file = self.data_path / f"{ticker}_{data_type}.parquet"
        if cache_file.exists():
            try:
                df = pd.read_parquet(cache_file)
                self.logger.info(f"Loaded {ticker} {data_type} data from cache")
                return df
            except Exception as e:
                self.logger.warning(f"Cache load failed: {str(e)}")
        return None