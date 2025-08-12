import asyncio
import logging
from pathlib import Path
import json
import os
import sys
from typing import Dict, Any

# Добавляем путь к папке проекта в PYTHONPATH
sys.path.append(str(Path(__file__).parent))

# Правильный импорт TradingBot
from scr.core.bot import TradingBot

class ConfigError(Exception):
    pass

async def load_config(path: Path) -> Dict[str, Any]:
    """Загрузка конфигурации с поддержкой переменных окружения"""
    try:
        config_content = path.read_text(encoding='utf-8')
        # Подстановка переменных окружения
        config_content = os.path.expandvars(config_content)
        config = json.loads(config_content)
        
        required = ['mode', 'api_source', 'tickers']
        if not all(key in config for key in required):
            raise ConfigError(f"Missing required keys: {required}")
            
        if config['mode'] not in ['train', 'paper', 'real']:
            raise ConfigError("Invalid mode in config")
            
        return config
        
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON: {str(e)}")
    except FileNotFoundError:
        raise ConfigError(f"Config file not found at {path.absolute()}")
    except Exception as e:
        raise ConfigError(f"Config loading failed: {str(e)}")

def setup_logging(config: Dict[str, Any]) -> None:
    """Настройка логирования с поддержкой переменных окружения"""
    logging_config = config.get('logging', {})
    
    # Получаем уровень логирования: сначала из переменной окружения, потом из конфига
    level = os.getenv('LOG_LEVEL', logging_config.get('level', 'INFO')).upper()
    
    # Проверяем валидность уровня логирования
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if level not in valid_levels:
        level = 'INFO'
        logging.warning(f"Invalid log level, defaulting to INFO. Valid levels: {valid_levels}")
    
    # Создаем папку для логов если не существует
    log_file = logging_config.get('file', 'logs/bot.log')
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Logging initialized with level {level}")

async def main():
    """Основная функция запуска бота"""
    try:
        # Загрузка конфигурации
        config_path = Path('config.json')
        logging.info(f"Loading config from {config_path.absolute()}")
        config = await load_config(config_path)
        
        # Настройка логирования
        setup_logging(config)
        logger = logging.getLogger('main')
        
        logger.info(f"Starting in {config['mode']} mode")
        logger.info(f"Tracking tickers: {', '.join(config['tickers'])}")
        
        # Инициализация и запуск бота
        bot = TradingBot(config)
        await bot.run()
        
    except ConfigError as e:
        logging.critical(f"Configuration error: {str(e)}")
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.critical(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        logging.info("Shutdown complete")

if __name__ == '__main__':
    asyncio.run(main())