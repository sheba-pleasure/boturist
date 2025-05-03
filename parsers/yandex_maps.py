from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from .base import BaseParser

logger = logging.getLogger(__name__)

class YandexMapsParser(BaseParser):
    """Парсер для Yandex.Maps"""
    
    BASE_URL = 'https://search-maps.yandex.ru/v1'
    
    def __init__(self, api_key: str, request_timeout: int = 30):
        super().__init__(api_key, request_timeout)
        self.default_params = {
            'apikey': self.api_key,
            'lang': 'ru_RU'
        }
    
    async def get_posts(self, source_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение отзывов о месте"""
        # В Yandex.Maps source_id - это business_id места
        params = {
            **self.default_params,
            'text': source_id,
            'type': 'biz',
            'results': 1
        }
        
        # Сначала получаем информацию о месте
        response = await self._make_request(self.BASE_URL, params)
        if not self._validate_response(response, ['features']) or not response['features']:
            return []
        
        place = response['features'][0]
        place_id = place['properties']['CompanyMetaData']['id']
        
        # Теперь получаем отзывы
        reviews = await self._get_reviews(place_id, limit)
        
        return [{
            'id': review['review_id'],
            'source_id': source_id,
            'text': review['text'],
            'rating': review['rating'],
            'created_at': self._parse_datetime(review['date']),
            'author': {
                'name': review['author'].get('name', 'Аноним'),
                'avatar_url': review['author'].get('avatar_url')
            },
            'likes_count': review.get('likes', 0),
            'platform': 'yandex_maps'
        } for review in reviews]
    
    async def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Получение ответов на отзыв"""
        # В Yandex.Maps комментарии к отзывам получаются вместе с отзывом
        # Этот метод оставлен для совместимости с базовым классом
        return []
    
    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о месте"""
        params = {
            **self.default_params,
            'text': profile_id,
            'type': 'biz',
            'results': 1
        }
        
        response = await self._make_request(self.BASE_URL, params)
        if not self._validate_response(response, ['features']) or not response['features']:
            return None
        
        place = response['features'][0]
        properties = place['properties']
        company_meta = properties['CompanyMetaData']
        
        return {
            'id': company_meta['id'],
            'name': company_meta['name'],
            'address': company_meta.get('address'),
            'categories': [category['name'] for category in company_meta.get('Categories', [])],
            'rating': properties.get('rating', {}).get('rating'),
            'reviews_count': properties.get('rating', {}).get('reviews_count', 0),
            'coordinates': place['geometry']['coordinates'],
            'hours': self._parse_working_hours(company_meta.get('Hours', {})),
            'phones': [phone['formatted'] for phone in company_meta.get('Phones', [])],
            'website': company_meta.get('url'),
            'platform': 'yandex_maps'
        }
    
    async def search_places(self, query: str, lat: float, lon: float, radius: int = 1000) -> List[Dict[str, Any]]:
        """Поиск мест по запросу в заданном радиусе"""
        params = {
            **self.default_params,
            'text': query,
            'type': 'biz',
            'll': f"{lon},{lat}",
            'spn': f"{radius/111000},{radius/111000}",  # Примерный перевод метров в градусы
            'results': 50
        }
        
        response = await self._make_request(self.BASE_URL, params)
        if not self._validate_response(response, ['features']):
            return []
        
        places = []
        for feature in response['features']:
            properties = feature['properties']
            company_meta = properties['CompanyMetaData']
            
            places.append({
                'id': company_meta['id'],
                'name': company_meta['name'],
                'address': company_meta.get('address'),
                'categories': [category['name'] for category in company_meta.get('Categories', [])],
                'rating': properties.get('rating', {}).get('rating'),
                'reviews_count': properties.get('rating', {}).get('reviews_count', 0),
                'coordinates': feature['geometry']['coordinates'],
                'distance': properties.get('distance'),  # Расстояние в метрах
                'platform': 'yandex_maps'
            })
        
        return places
    
    async def _get_reviews(self, place_id: str, limit: int) -> List[Dict[str, Any]]:
        """Получение отзывов о месте"""
        params = {
            **self.default_params,
            'business_id': place_id,
            'limit': min(limit, 50)  # Яндекс ограничивает количество отзывов
        }
        
        response = await self._make_request(f"{self.BASE_URL}/reviews", params)
        if not self._validate_response(response, ['reviews']):
            return []
        
        return response['reviews']
    
    def _parse_working_hours(self, hours: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг графика работы"""
        if not hours or 'Availabilities' not in hours:
            return None
        
        schedule = {}
        for availability in hours['Availabilities']:
            # Преобразуем дни недели из Яндекс формата в человекочитаемый
            days = {
                1: 'Понедельник',
                2: 'Вторник',
                3: 'Среда',
                4: 'Четверг',
                5: 'Пятница',
                6: 'Суббота',
                7: 'Воскресенье'
            }
            
            for interval in availability.get('Intervals', []):
                from_time = interval.get('from')
                to_time = interval.get('to')
                if from_time and to_time:
                    day_name = days.get(availability.get('Monday', 1))
                    if day_name:
                        schedule[day_name] = f"{from_time}-{to_time}"
        
        return schedule if schedule else None 