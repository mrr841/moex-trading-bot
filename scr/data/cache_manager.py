import asyncio
import pickle
import zlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging
import cachetools
import aiofiles
import pandas as pd

logger = logging.getLogger(__name__)

class CacheManager:
    """Многоуровневый кэш-менеджер для торгового бота"""

    def __init__(self):
        self.memory_cache = cachetools.TTLCache(maxsize=1000, ttl=3600)  # 1 час в памяти
        self.disk_cache_dir = Path("data/cache")
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        self.locks: Dict[str, asyncio.Lock] = {}

    def _get_cache_path(self, key: str) -> Path:
        """Генерация пути к файлу кэша"""
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self.disk_cache_dir / f"{safe_key}.cache"

    async def get_lock(self, key: str) -> asyncio.Lock:
        """Получение блокировки для ключа"""
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]

    async def get(self, key: str) -> Any:
        """Получение данных из кэша"""
        # 1. Проверка в памяти
        if key in self.memory_cache:
            logger.debug(f"Memory cache hit: {key}")
            return self.memory_cache[key]

        # 2. Проверка на диске
        cache_file = self._get_cache_path(key)
        if not cache_file.exists():
            return None

        async with await self.get_lock(key):
            try:
                async with aiofiles.open(cache_file, "rb") as f:
                    data = await f.read()
                    uncompressed = zlib.decompress(data)
                    result = pickle.loads(uncompressed)
                    
                    # Обновляем memory cache
                    self.memory_cache[key] = result
                    logger.debug(f"Disk cache hit: {key}")
                    return result
            except Exception as e:
                logger.error(f"Cache read error for {key}: {str(e)}")
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Сохранение данных в кэш"""
        if value is None:
            return False

        async with await self.get_lock(key):
            try:
                # 1. Сохраняем в memory cache
                self.memory_cache[key] = value

                # 2. Сериализуем для disk cache
                serialized = pickle.dumps(value)
                compressed = zlib.compress(serialized)

                # 3. Сохраняем на диск
                cache_file = self._get_cache_path(key)
                async with aiofiles.open(cache_file, "wb") as f:
                    await f.write(compressed)

                logger.debug(f"Cache set: {key}")
                return True
            except Exception as e:
                logger.error(f"Cache write error for {key}: {str(e)}")
                return False

    async def invalidate(self, key: str) -> None:
        """Удаление данных из кэша"""
        async with await self.get_lock(key):
            # 1. Удаляем из memory
            self.memory_cache.pop(key, None)

            # 2. Удаляем с диска
            cache_file = self._get_cache_path(key)
            if cache_file.exists():
                cache_file.unlink()

            logger.debug(f"Cache invalidated: {key}")

    async def cleanup(self, older_than_days: int = 7) -> None:
        """Очистка устаревших кэш-файлов"""
        now = datetime.now()
        cutoff = now - timedelta(days=older_than_days)

        for cache_file in self.disk_cache_dir.glob("*.cache"):
            stat = cache_file.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            
            if last_modified < cutoff:
                async with await self.get_lock(cache_file.stem):
                    cache_file.unlink()
                    logger.info(f"Cleaned up old cache: {cache_file.name}")

    async def get_dataframe(self, key: str) -> Optional[pd.DataFrame]:
        """Специализированный метод для DataFrame"""
        data = await self.get(key)
        if isinstance(data, pd.DataFrame):
            return data
        return None

    async def set_dataframe(self, key: str, df: pd.DataFrame) -> bool:
        """Специализированный метод для DataFrame"""
        if not isinstance(df, pd.DataFrame):
            return False
        return await self.set(key, df)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()