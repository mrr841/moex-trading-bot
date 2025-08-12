"""
Unit Tests Package - тестирование отдельных компонентов системы

Содержит:
- Тесты модуля данных (DataHandler, CacheManager)
- Тесты технических индикаторов
- Тесты риск-менеджмента
- Тесты вспомогательных утилит
"""

# Импорт общих фикстур из корневого conftest.py
pytest_plugins = [
    'conftest'
]

# Реэкспорт типов для удобства импорта в тестах
from src.core import BotState
from src.managers import SignalType
from src.trading import OrderStatus

__all__ = [
    'BotState',
    'SignalType',
    'OrderStatus'
]

# Настройка логгирования тестов
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('unit-tests')

def pytest_sessionstart(session):
    """Инициализация перед запуском всех тестов"""
    logger.info("Starting unit tests suite...")

def pytest_sessionfinish(session):
    """Финализация после выполнения всех тестов"""
    logger.info("Unit tests completed")