"""
Core package of the trading bot.

Contains main bot class and state management system.
"""

from .bot import TradingBot
from .state_manager import StateManager, BotState
from ..utils.helpers import validate_config

import logging
from pathlib import Path

__all__ = ['TradingBot', 'StateManager', 'BotState']  # Экспортируемые объекты
__version__ = '0.1.0'

# Инициализация логгера пакета
_logger = logging.getLogger(__name__)
_logger.info(f"Initializing core package v{__version__}")

def check_dependencies() -> bool:
    """Проверка обязательных зависимостей для пакета core"""
    try:
        import aiohttp
        import pandas
        return True
    except ImportError as e:
        _logger.critical(f"Missing core dependency: {str(e)}")
        return False

# Автопроверка при импорте пакета
if not check_dependencies():
    raise RuntimeError("Core package dependencies not satisfied")

# Путь к директории core (для внутреннего использования)
CORE_DIR = Path(__file__).parent