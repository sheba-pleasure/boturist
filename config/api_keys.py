from typing import Dict, Optional
import os
from django.conf import settings
import json
from redis import Redis
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class APIKeyManager:
    def __init__(self):
        """Initialize Redis connection for API key storage"""
        self.redis = Redis.from_url(settings.REDIS_URL)
        self.key_prefix = "api_keys:"
    
    def set_key(self, service: str, key: str, expires_in_days: Optional[int] = None) -> bool:
        """
        Store API key for a service
        :param service: Service name (e.g., 'vk', 'telegram')
        :param key: API key
        :param expires_in_days: Optional expiration in days
        """
        try:
            key_data = {
                'key': key,
                'created_at': datetime.utcnow().isoformat(),
                'last_used': None
            }
            
            redis_key = f"{self.key_prefix}{service}"
            self.redis.set(redis_key, json.dumps(key_data))
            
            if expires_in_days:
                self.redis.expire(redis_key, timedelta(days=expires_in_days))
            
            return True
        except Exception as e:
            logger.error(f"Error setting API key for {service}: {e}")
            return False
    
    def get_key(self, service: str) -> Optional[str]:
        """Get API key for a service"""
        try:
            redis_key = f"{self.key_prefix}{service}"
            key_data = self.redis.get(redis_key)
            
            if not key_data:
                return None
            
            data = json.loads(key_data)
            
            # Update last used timestamp
            data['last_used'] = datetime.utcnow().isoformat()
            self.redis.set(redis_key, json.dumps(data))
            
            return data['key']
        except Exception as e:
            logger.error(f"Error getting API key for {service}: {e}")
            return None
    
    def delete_key(self, service: str) -> bool:
        """Delete API key for a service"""
        try:
            redis_key = f"{self.key_prefix}{service}"
            return bool(self.redis.delete(redis_key))
        except Exception as e:
            logger.error(f"Error deleting API key for {service}: {e}")
            return False
    
    def list_services(self) -> Dict[str, Dict]:
        """List all services with API keys and their metadata"""
        try:
            services = {}
            for key in self.redis.scan_iter(f"{self.key_prefix}*"):
                service = key.decode('utf-8').replace(self.key_prefix, '')
                data = json.loads(self.redis.get(key))
                services[service] = {
                    'created_at': data['created_at'],
                    'last_used': data['last_used']
                }
            return services
        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return {} 