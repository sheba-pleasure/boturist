from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import re

from .base import BaseParser
from .metrics import MetricsMiddleware

logger = logging.getLogger(__name__)

class InstagramParser(BaseParser):
    """Парсер для Instagram"""
    
    BASE_URL = 'https://graph.instagram.com/v18.0'
    
    def __init__(self, api_key: str, request_timeout: int = 30):
        super().__init__(api_key, request_timeout)
        self.default_params = {
            'access_token': self.api_key
        }
    
    @MetricsMiddleware(platform="instagram")
    async def get_posts(self, source_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение постов из профиля"""
        params = {
            **self.default_params,
            'fields': 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{media_url,media_type}',
            'limit': min(limit, 50)  # Instagram ограничивает максимальное количество
        }
        
        response = await self._make_request(f"{self.BASE_URL}/{source_id}/media", params)
        if not self._validate_response(response, ['data']):
            return []
        
        posts = []
        for item in response['data']:
            post = {
                'id': item['id'],
                'source_id': source_id,
                'text': item.get('caption', ''),
                'created_at': self._parse_datetime(item['timestamp']),
                'url': item['permalink'],
                'media_type': item['media_type'],
                'media': self._parse_media(item),
                'platform': 'instagram'
            }
            posts.append(post)
        
        return posts
    
    @MetricsMiddleware(platform="instagram")
    async def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Получение комментариев к посту"""
        params = {
            **self.default_params,
            'fields': 'text,timestamp,username,replies{text,timestamp,username}'
        }
        
        response = await self._make_request(f"{self.BASE_URL}/{post_id}/comments", params)
        if not self._validate_response(response, ['data']):
            return []
        
        comments = []
        for item in response['data']:
            comment = {
                'id': item['id'],
                'post_id': post_id,
                'text': item['text'],
                'created_at': self._parse_datetime(item['timestamp']),
                'author': {
                    'username': item['username']
                },
                'platform': 'instagram'
            }
            comments.append(comment)
            
            # Добавляем ответы на комментарий
            replies = item.get('replies', {}).get('data', [])
            for reply in replies:
                reply_data = {
                    'id': reply['id'],
                    'post_id': post_id,
                    'parent_id': item['id'],
                    'text': reply['text'],
                    'created_at': self._parse_datetime(reply['timestamp']),
                    'author': {
                        'username': reply['username']
                    },
                    'platform': 'instagram'
                }
                comments.append(reply_data)
        
        return comments
    
    @MetricsMiddleware(platform="instagram")
    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о профиле"""
        params = {
            **self.default_params,
            'fields': 'id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count,website'
        }
        
        response = await self._make_request(f"{self.BASE_URL}/{profile_id}", params)
        if not self._validate_response(response, ['id']):
            return None
        
        return {
            'id': response['id'],
            'username': response['username'],
            'name': response.get('name', ''),
            'avatar_url': response.get('profile_picture_url'),
            'bio': response.get('biography', ''),
            'followers_count': response.get('followers_count', 0),
            'following_count': response.get('follows_count', 0),
            'posts_count': response.get('media_count', 0),
            'website': response.get('website'),
            'platform': 'instagram'
        }
    
    def _parse_media(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Парсинг медиа-контента поста"""
        media = []
        
        if item['media_type'] == 'IMAGE':
            media.append({
                'type': 'image',
                'url': item['media_url']
            })
        
        elif item['media_type'] == 'VIDEO':
            media.append({
                'type': 'video',
                'url': item['media_url'],
                'thumbnail_url': item.get('thumbnail_url')
            })
        
        elif item['media_type'] == 'CAROUSEL_ALBUM':
            children = item.get('children', {}).get('data', [])
            for child in children:
                if child['media_type'] == 'IMAGE':
                    media.append({
                        'type': 'image',
                        'url': child['media_url']
                    })
                elif child['media_type'] == 'VIDEO':
                    media.append({
                        'type': 'video',
                        'url': child['media_url'],
                        'thumbnail_url': child.get('thumbnail_url')
                    })
        
        return media
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Извлечение упоминаний пользователей из текста"""
        return re.findall(r'@(\w+)', text)
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Извлечение хэштегов из текста"""
        return re.findall(r'#(\w+)', text) 