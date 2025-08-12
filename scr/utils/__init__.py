"""
Utils Module - вспомогательные инструменты и интеграции

Содержит:
- Генератор отчетов и аналитики
- Telegram-интерфейс для управления и уведомлений
- Вспомогательные функции общего назначения
"""

from .reporting import (
    generate_trade_report,
    generate_performance_analytics,
    create_backtest_visualization,
    prepare_daily_summary
)

from .telegram_interface import (
    TelegramBot,
    send_alert,
    format_trade_message,
    format_signal_message
)

from .helpers import (
    async_retry,
    calculate_pnl,
    format_price,
    parse_timedelta,
    validate_config
)

from typing import Optional, Dict, Any, List
from enum import Enum, auto
import logging
from pathlib import Path
import json

__all__ = [
    # Reporting
    'generate_trade_report',
    'generate_performance_analytics',
    'create_backtest_visualization',
    'prepare_daily_summary',
    
    # Telegram
    'TelegramBot',
    'send_alert',
    'format_trade_message',
    'format_signal_message',
    
    # Helpers
    'async_retry',
    'calculate_pnl',
    'format_price',
    'parse_timedelta',
    'validate_config',
    
    # Types
    'ReportType',
    'TelegramCommand'
]

__version__ = '1.4.0'

class ReportType(Enum):
    TRADE = auto()
    PERFORMANCE = auto()
    RISK = auto()
    OVERNIGHT = auto()

class TelegramCommand(Enum):
    START = "/start"
    STATS = "/stats"
    POSITIONS = "/positions"
    STOP = "/stop"
    CONFIG = "/config"

# Настройка логгера модуля
_logger = logging.getLogger(__name__)
_logger.info(f'Utils module v{__version__} initialized')

# Константы модуля
MAX_RETRIES = 3
RETRY_DELAY = 1.0
REPORTS_DIR = Path("reports")
TELEGRAM_FORMAT_VERSION = "1.0"

def init_utils(config: Dict) -> None:
    """Инициализация утилит"""
    REPORTS_DIR.mkdir(exist_ok=True)
    
    # Валидация конфига Telegram
    if config.get('telegram', {}).get('enabled', False):
        required = ['token', 'chat_id']
        if not all(k in config['telegram'] for k in required):
            _logger.warning("Telegram enabled but config incomplete")

def load_json_schema(schema_name: str) -> Optional[Dict]:
    """Загрузка JSON-схемы для валидации"""
    schema_path = Path(__file__).parent / 'schemas' / f'{schema_name}.json'
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        _logger.error(f"Failed to load schema {schema_name}: {str(e)}")
        return None