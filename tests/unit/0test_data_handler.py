import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd
from datetime import datetime, timedelta
from src.data.data_handler import DataHandler

@pytest.fixture
def mock_config():
    return {
        'api_source': 'tinkoff_paper',
        'tickers': ['SBER', 'GAZP'],
        'timeframe': '1h',
        'api_settings': {
            'tinkoff': {
                'token': 'test_token',
                'account_id': 'test_account'
            }
        }
    }

@pytest.fixture
def sample_ohlcv_data():
    dates = pd.date_range(end=datetime.now(), periods=10, freq='1h')
    return pd.DataFrame({
        'open': [100 + i for i in range(10)],
        'high': [105 + i for i in range(10)],
        'low': [95 + i for i in range(10)],
        'close': [102 + i for i in range(10)],
        'volume': [1000 * i for i in range(1, 11)]
    }, index=dates)

@pytest.mark.asyncio
async def test_fetch_moex_candles(mock_config, sample_ohlcv_data):
    """Тест получения свечных данных с MOEX"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'candles': {
                'columns': ['open', 'high', 'low', 'close', 'volume', 'begin'],
                'data': [
                    [row['open'], row['high'], row['low'], row['close'], row['volume'], str(idx)]
                    for idx, row in sample_ohlcv_data.iterrows()
                ]
            }
        }
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response

        async with DataHandler(mock_config) as handler:
            data = await handler.fetch_moex_candles('SBER', '1h', '2023-01-01', '2023-01-02')
            
            assert isinstance(data, pd.DataFrame)
            assert len(data) == 10
            assert 'close' in data.columns

@pytest.mark.asyncio
async def test_get_orderbook(mock_config):
    """Тест получения стакана цен"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'orderbook': {
                'data': {
                    'bids': [[250.0, 100], [249.5, 50]],
                    'asks': [[250.5, 200], [251.0, 150]]
                }
            }
        }
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response

        async with DataHandler(mock_config) as handler:
            orderbook = await handler.get_orderbook('SBER')
            
            assert 'bids' in orderbook
            assert 'asks' in orderbook
            assert len(orderbook['bids']) == 2

@pytest.mark.asyncio
async def test_cache_operations(mock_config, sample_ohlcv_data):
    """Тест кэширования данных"""
    with patch('src.data.data_handler.DataHandler._fetch_moex_candles', 
              return_value=sample_ohlcv_data) as mock_fetch:
        async with DataHandler(mock_config) as handler:
            # Первый вызов - данные должны быть загружены
            data1 = await handler.get_ticker_data('SBER', '1h')
            assert mock_fetch.called
            
            # Второй вызов - данные должны быть взяты из кэша
            mock_fetch.reset_mock()
            data2 = await handler.get_ticker_data('SBER', '1h')
            assert not mock_fetch.called
            assert data1.equals(data2)

@pytest.mark.asyncio
async def test_error_handling(mock_config):
    """Тест обработки ошибок API"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Server Error"
        mock_get.return_value.__aenter__.return_value = mock_response

        async with DataHandler(mock_config) as handler:
            with pytest.raises(Exception) as excinfo:
                await handler.fetch_moex_candles('SBER', '1h', '2023-01-01', '2023-01-02')
            assert "Server Error" in str(excinfo.value)

def test_convert_timeframe(mock_config):
    """Тест конвертации таймфреймов"""
    async def test_wrapper():
        async with DataHandler(mock_config) as handler:
            assert handler._convert_timeframe('1m') == 1
            assert handler._convert_timeframe('5m') == 5
            assert handler._convert_timeframe('1h') == 60
            assert handler._convert_timeframe('1d') == 24
            
            with pytest.raises(KeyError):
                handler._convert_timeframe('invalid')
    
    # Запуск асинхронного теста
    import asyncio
    asyncio.run(test_wrapper())