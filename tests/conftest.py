import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta

@pytest.fixture
def sample_candles():
    """Фикстура с тестовыми свечами"""
    date_range = pd.date_range(end=datetime.now(), periods=100, freq='1min')
    data = {
        'open': [100 + i for i in range(100)],
        'high': [101 + i for i in range(100)],
        'low': [99 + i for i in range(100)],
        'close': [100 + i for i in range(100)],
        'volume': [1000 + i*10 for i in range(100)]
    }
    return pd.DataFrame(data, index=date_range)

@pytest.fixture
def mock_config():
    """Фикстура с моком конфига"""
    return {
        'tickers': ['SBER', 'GAZP'],
        'max_active_positions': 5,
        'timeframe': '1min',
        'risk_management': {
            'stop_loss': 0.05,
            'trailing_stop': 0.03
        }
    }

@pytest.fixture
def mock_api_client():
    """Фикстура с моком API клиента"""
    mock = MagicMock()
    mock.get_candles.return_value = sample_candles()
    return mock