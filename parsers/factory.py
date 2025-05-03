from typing import Dict, Type
from .base import BaseParser
from .vk import VKParser
from .instagram import InstagramParser
from .yandex_maps import YandexMapsParser

class ParserFactory:
    """Фабрика для создания парсеров социальных сетей"""
    
    _parsers: Dict[str, Type[BaseParser]] = {
        'vk': VKParser,
        'instagram': InstagramParser,
        'yandex_maps': YandexMapsParser
    }
    
    @classmethod
    def get_parser(cls, platform: str, api_key: str, **kwargs) -> BaseParser:
        """
        Создает и возвращает парсер для указанной платформы
        
        Args:
            platform: Название платформы ('vk', 'instagram', 'yandex_maps')
            api_key: API ключ для платформы
            **kwargs: Дополнительные параметры для парсера
        
        Returns:
            BaseParser: Экземпляр парсера для указанной платформы
            
        Raises:
            ValueError: Если платформа не поддерживается
        """
        parser_class = cls._parsers.get(platform.lower())
        if not parser_class:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return parser_class(api_key, **kwargs)
    
    @classmethod
    def supported_platforms(cls) -> list[str]:
        """Возвращает список поддерживаемых платформ"""
        return list(cls._parsers.keys()) 