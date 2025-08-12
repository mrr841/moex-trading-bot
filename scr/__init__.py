"""
Trading Bot Package - основной пакет торгового бота

Содержит все модули для работы торговой системы:
- Ядро бота и управление состоянием
- Обработку данных и индикаторы
- Управление стратегиями и рисками
- Исполнение сделок и интеграции
"""

# Основные экспорты из подмодулей
from .core import TradingBot, StateManager
from .data import DataHandler, CacheManager
from .indicators import (
    calculate_adx,
    calculate_rsi,
    fractal_breakout_detector,
    volume_spike_detector
)
from .managers import (
    StrategyManager,
    RiskManager,
    MarketRegimeDetector,
    OvernightManager
)
from .trading import TradeExecutor, Order, ExecutionReport
from .utils import (
    generate_trade_report,
    TelegramBot,
    format_price,
    async_retry
)

# Версия пакета
__version__ = '1.0.0'

# Типы данных для экспорта
__all__ = [
    # Core
    'TradingBot',
    'StateManager',
    
    # Data
    'DataHandler',
    'CacheManager',
    
    # Indicators
    'calculate_adx',
    'calculate_rsi',
    'fractal_breakout_detector',
    'volume_spike_detector',
    
    # Managers
    'StrategyManager',
    'RiskManager',
    'MarketRegimeDetector',
    'OvernightManager',
    
    # Trading
    'TradeExecutor',
    'Order',
    'ExecutionReport',
    
    # Utils
    'generate_trade_report',
    'TelegramBot',
    'format_price',
    'async_retry',
    
    # Types
    'BotState',
    'SignalType',
    'MarketRegime',
    'OrderType'
]

# Инициализация логгера пакета
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)
_logger.info(f'Trading Bot package v{__version__} initialized')

# Константы пакета
CONFIG_DIR = Path(__file__).parent.parent / 'config'
DATA_DIR = Path(__file__).parent.parent / 'data'
LOGS_DIR = Path(__file__).parent.parent / 'logs'

def init_package():
    """Инициализация директорий пакета"""
    for directory in [CONFIG_DIR, DATA_DIR, LOGS_DIR]:
        directory.mkdir(exist_ok=True)
    
    _logger.debug("Package directories initialized")

# Автоматическая инициализация при импорте
init_package()

# Реэкспорт типов из подмодулей
from .core.bot import BotState
from .managers.strategy_manager import SignalType
from .managers.regime_detector import MarketRegime
from .trading.trade_executor import OrderType