from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from .metrics import MetricsMiddleware, start_metrics_server

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Базовый класс для парсеров социальных сетей"""
    
    def __init__(self, api_key: str, request_timeout: int = 30):
        self.api_key = api_key
        self.request_timeout = request_timeout
        self.session = None
        # Запускаем сервер метрик при создании первого парсера
        try:
            start_metrics_server()
        except OSError:
            # Сервер уже запущен
            pass
    
    async def __aenter__(self):
        """Создаем сессию при входе в контекстный менеджер"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрываем сессию при выходе из контекстного менеджера"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    @MetricsMiddleware(platform="base")
    async def get_posts(self, source_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение постов из источника"""
        pass
    
    @abstractmethod
    @MetricsMiddleware(platform="base")
    async def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Получение комментариев к посту"""
        pass
    
    @abstractmethod
    @MetricsMiddleware(platform="base")
    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о профиле"""
        pass
    
    async def _make_request(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Выполнение HTTP запроса с обработкой ошибок"""
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit exceeded. Waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(url, params)
                
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during request: {e}")
            return None
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """Парсинг даты/времени из строки"""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse datetime: {date_str}")
            return datetime.now()
    
    def _validate_response(self, response: Optional[Dict[str, Any]], required_fields: List[str]) -> bool:
        """Проверка наличия необходимых полей в ответе"""
        if not response:
            return False
            
        return all(field in response for field in required_fields) 