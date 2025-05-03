import vk_api
from typing import Dict, List, Optional
from datetime import datetime
import logging
from celery import shared_task

logger = logging.getLogger(__name__)

class VKParser:
    def __init__(self, token: str):
        """Initialize VK API connection"""
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()
    
    def get_group_posts(self, group_id: str, count: int = 100) -> List[Dict]:
        """Get posts from VK group"""
        try:
            posts = self.vk.wall.get(owner_id=group_id, count=count)
            return posts['items']
        except Exception as e:
            logger.error(f"Error getting VK posts: {e}")
            return []
    
    def get_comments(self, group_id: str, post_id: int) -> List[Dict]:
        """Get comments for a specific post"""
        try:
            comments = self.vk.wall.getComments(
                owner_id=group_id,
                post_id=post_id,
                need_likes=1,
                count=100
            )
            return comments['items']
        except Exception as e:
            logger.error(f"Error getting VK comments: {e}")
            return []

@shared_task
def parse_vk_group(group_id: str, token: str) -> None:
    """Celery task to parse VK group"""
    parser = VKParser(token)
    posts = parser.get_group_posts(group_id)
    
    for post in posts:
        # Get comments for each post
        comments = parser.get_comments(group_id, post['id'])
        
        # Save to MongoDB for further processing
        save_to_mongodb(post, comments)

def save_to_mongodb(post: Dict, comments: List[Dict]) -> None:
    """Save parsed data to MongoDB"""
    from pymongo import MongoClient
    from django.conf import settings
    
    client = MongoClient(settings.MONGODB_URI)
    db = client.social_media
    
    # Save post with its comments
    db.vk_posts.update_one(
        {'id': post['id']},
        {
            '$set': {
                'post': post,
                'comments': comments,
                'updated_at': datetime.utcnow()
            }
        },
        upsert=True
    ) 