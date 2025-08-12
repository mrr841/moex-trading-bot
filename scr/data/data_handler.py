import aiohttp
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
import cachetools
import pytz

from .cache_manager import CacheManager
from ..utils.helpers import async_retry

logger = logging.getLogger(__name__)

class DataHandler:
    """Обработчик данных для MOEX ISS и Tinkoff Invest API"""

    def __init__(self, config: dict):
        self.config = config
        self.cache = CacheManager()
        self.session = None
        self.tz = pytz.timezone('Europe/Moscow')
        
        # API endpoints
        self.moex_base_url = "https://iss.moex.com/iss"
        self.tinkoff_base_url = "https://invest-public-api.tinkoff.ru/rest"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers=self._get_headers()
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> dict:
        """Возвращает заголовки для API"""
        if self.config['api_source'].startswith('tinkoff'):
            return {
                'Authorization': f"Bearer {self.config['api_settings']['tinkoff']['token']}",
                'Content-Type': 'application/json'
            }
        return {}

    @async_retry(max_retries=3, delay=1)
    async def get_ticker_data(self, ticker: str, timeframe: str) -> pd.DataFrame:
        """Получение данных по тикеру"""
        cache_key = f"{ticker}_{timeframe}"
        if cached := await self.cache.get(cache_key):
            return cached

        if self.config['api_source'].startswith('moex'):
            data = await self._fetch_moex_candles(ticker, timeframe)
        else:
            data = await self._fetch_tinkoff_candles(ticker, timeframe)

        await self.cache.set(cache_key, data)
        return data

    async def _fetch_moex_candles(self, ticker: str, timeframe: str) -> pd.DataFrame:
        """Получение исторических данных с MOEX ISS"""
        url = f"{self.moex_base_url}/engines/stock/markets/shares/securities/{ticker}/candles.json"
        params = {
            'interval': self._convert_timeframe(timeframe),
            'from': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        }

        async with self.session.get(url, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()

        df = pd.DataFrame(data['candles']['data'], columns=data['candles']['columns'])
        df['begin'] = pd.to_datetime(df['begin']).dt.tz_localize(self.tz)
        df.set_index('begin', inplace=True)
        return df

    async def _fetch_tinkoff_candles(self, ticker: str, timeframe: str) -> pd.DataFrame:
        """Получение свечей с Tinkoff API"""
        figi = await self._get_figi(ticker)
        endpoint = f"{self.tinkoff_base_url}/tinkoff.public.invest.api.contract.v1.MarketDataService/GetCandles"
        
        payload = {
            "figi": figi,
            "from": (datetime.now() - timedelta(days=30)).isoformat() + 'Z',
            "to": datetime.utcnow().isoformat() + 'Z',
            "interval": self._convert_tinkoff_timeframe(timeframe)
        }

        async with self.session.post(endpoint, json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()

        candles = []
        for candle in data['candles']:
            candles.append({
                'open': self._quotation_to_float(candle['open']),
                'high': self._quotation_to_float(candle['high']),
                'low': self._quotation_to_float(candle['low']),
                'close': self._quotation_to_float(candle['close']),
                'volume': candle['volume'],
                'time': pd.to_datetime(candle['time']).tz_convert(self.tz)
            })

        df = pd.DataFrame(candles)
        df.set_index('time', inplace=True)
        return df

    async def _get_figi(self, ticker: str) -> str:
        """Получение FIGI по тикеру"""
        if cached := await self.cache.get(f"figi_{ticker}"):
            return cached

        endpoint = f"{self.tinkoff_base_url}/tinkoff.public.invest.api.contract.v1.InstrumentsService/Shares"
        async with self.session.post(endpoint) as resp:
            resp.raise_for_status()
            data = await resp.json()

        for share in data['instruments']:
            if share['ticker'] == ticker:
                await self.cache.set(f"figi_{ticker}", share['figi'])
                return share['figi']

        raise ValueError(f"FIGI not found for {ticker}")

    async def get_orderbook(self, ticker: str, depth: int = 10) -> dict:
        """Получение стакана"""
        if self.config['api_source'].startswith('moex'):
            url = f"{self.moex_base_url}/engines/stock/markets/shares/securities/{ticker}/orderbook.json"
            async with self.session.get(url) as resp:
                data = await resp.json()
            return {
                'bids': [(float(b[0]), int(b[1])) for b in data['orderbook']['data']['bids']],
                'asks': [(float(a[0]), int(a[1])) for a in data['orderbook']['data']['asks']]
            }
        else:
            endpoint = f"{self.tinkoff_base_url}/tinkoff.public.invest.api.contract.v1.MarketDataService/GetOrderBook"
            payload = {
                "figi": await self._get_figi(ticker),
                "depth": depth
            }
            async with self.session.post(endpoint, json=payload) as resp:
                data = await resp.json()
            return {
                'bids': [(self._quotation_to_float(b['price']), b['quantity']) for b in data['bids']],
                'asks': [(self._quotation_to_float(a['price']), a['quantity']) for a in data['asks']]
            }

    @staticmethod
    def _convert_timeframe(timeframe: str) -> int:
        """Конвертация таймфрейма для MOEX"""
        tf_map = {'1m': 1, '5m': 5, '10m': 10, '1h': 60, '1d': 24}
        return tf_map.get(timeframe, 1)

    @staticmethod
    def _convert_tinkoff_timeframe(timeframe: str) -> str:
        """Конвертация таймфрейма для Tinkoff"""
        tf_map = {
            '1m': 'CANDLE_INTERVAL_1_MIN',
            '5m': 'CANDLE_INTERVAL_5_MIN',
            '1h': 'CANDLE_INTERVAL_HOUR',
            '1d': 'CANDLE_INTERVAL_DAY'
        }
        return tf_map.get(timeframe, 'CANDLE_INTERVAL_1_MIN')

    @staticmethod
    def _quotation_to_float(q: dict) -> float:
        """Конвертация Quotation в float"""
        return q['units'] + q['nano'] / 1e9

    async def get_last_price(self, ticker: str) -> float:
        """Получение последней цены"""
        orderbook = await self.get_orderbook(ticker, 1)
        return (orderbook['bids'][0][0] + orderbook['asks'][0][0]) / 2