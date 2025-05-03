from typing import Dict, Any, List
import asyncio
from abc import ABC, abstractmethod
import logging

import vk_api
import instaloader
from playwright.async_api import async_playwright

from config import Config

logger = logging.getLogger(__name__)

class SocialMediaParser(ABC):
    """Abstract base class for social media parsers"""
    
    @abstractmethod
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Get messages from social media"""
        pass
    
    @abstractmethod
    async def get_comments(self) -> List[Dict[str, Any]]:
        """Get comments from social media"""
        pass
    
    @abstractmethod
    async def post_reply(self, message_id: str, text: str) -> bool:
        """Post reply to a message"""
        pass

class VKParser(SocialMediaParser):
    """VK social media parser"""
    
    def __init__(self):
        """Initialize VK parser"""
        self.vk_session = vk_api.VkApi(token=Config.VK_API_TOKEN)
        self.vk = self.vk_session.get_api()
    
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Get messages from VK"""
        try:
            messages = await asyncio.to_thread(
                self.vk.messages.get,
                count=100,
                filter="unread"
            )
            
            return [
                {
                    "id": msg["id"],
                    "from_id": msg["from_id"],
                    "text": msg["text"],
                    "date": msg["date"],
                    "platform": "vk"
                }
                for msg in messages["items"]
            ]
        except Exception as e:
            logger.error(f"Error getting VK messages: {e}")
            return []
    
    async def get_comments(self) -> List[Dict[str, Any]]:
        """Get comments from VK group"""
        try:
            comments = await asyncio.to_thread(
                self.vk.wall.getComments,
                owner_id=Config.VK_GROUP_ID,
                count=100
            )
            
            return [
                {
                    "id": comment["id"],
                    "from_id": comment["from_id"],
                    "text": comment["text"],
                    "date": comment["date"],
                    "platform": "vk"
                }
                for comment in comments["items"]
            ]
        except Exception as e:
            logger.error(f"Error getting VK comments: {e}")
            return []
    
    async def post_reply(self, message_id: str, text: str) -> bool:
        """Post reply to VK message"""
        try:
            await asyncio.to_thread(
                self.vk.messages.send,
                peer_id=message_id,
                message=text,
                random_id=0
            )
            return True
        except Exception as e:
            logger.error(f"Error posting VK reply: {e}")
            return False

class InstagramParser(SocialMediaParser):
    """Instagram parser using instaloader"""
    
    def __init__(self):
        """Initialize Instagram parser"""
        self.loader = instaloader.Instaloader()
        self.loader.login(Config.INSTAGRAM_USERNAME, Config.INSTAGRAM_PASSWORD)
    
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Get Instagram direct messages"""
        # Note: Instagram's API has limitations for DM access
        # This is a placeholder for future implementation
        return []
    
    async def get_comments(self) -> List[Dict[str, Any]]:
        """Get Instagram post comments"""
        try:
            profile = await asyncio.to_thread(
                instaloader.Profile.from_username,
                self.loader.context,
                Config.INSTAGRAM_USERNAME
            )
            
            comments = []
            posts = profile.get_posts()
            
            for post in posts:
                post_comments = post.get_comments()
                comments.extend([
                    {
                        "id": comment.id,
                        "from_id": comment.owner.userid,
                        "text": comment.text,
                        "date": comment.created_at_utc,
                        "platform": "instagram"
                    }
                    for comment in post_comments
                ])
            
            return comments
        except Exception as e:
            logger.error(f"Error getting Instagram comments: {e}")
            return []
    
    async def post_reply(self, message_id: str, text: str) -> bool:
        """Post reply to Instagram comment"""
        # Note: Instagram's API has limitations for automated responses
        # This is a placeholder for future implementation
        return False

class YandexMapsParser:
    """Parser for Yandex.Maps reviews"""
    
    async def get_reviews(self, business_id: str) -> List[Dict[str, Any]]:
        """Get reviews from Yandex.Maps"""
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                # Navigate to business page
                await page.goto(f"https://yandex.ru/maps/org/{business_id}")
                
                # Wait for reviews to load
                await page.wait_for_selector(".business-reviews-card")
                
                # Extract reviews
                reviews = await page.evaluate("""
                    () => {
                        const reviews = [];
                        document.querySelectorAll('.business-reviews-card').forEach(review => {
                            reviews.push({
                                text: review.querySelector('.business-review-view__body-text').innerText,
                                rating: review.querySelector('.business-rating-badge-view__rating').innerText,
                                author: review.querySelector('.business-review-view__author').innerText,
                                date: review.querySelector('.business-review-view__date').innerText
                            });
                        });
                        return reviews;
                    }
                """)
                
                await browser.close()
                return reviews
            
            except Exception as e:
                logger.error(f"Error getting Yandex.Maps reviews: {e}")
                return []

class SocialMediaHub:
    """Hub for managing multiple social media parsers"""
    
    def __init__(self):
        """Initialize social media hub"""
        self.parsers = {
            "vk": VKParser(),
            "instagram": InstagramParser(),
            "yandex_maps": YandexMapsParser()
        }
    
    async def get_all_messages(self) -> List[Dict[str, Any]]:
        """Get messages from all platforms"""
        all_messages = []
        
        for platform, parser in self.parsers.items():
            if isinstance(parser, SocialMediaParser):
                messages = await parser.get_messages()
                all_messages.extend(messages)
        
        return all_messages
    
    async def get_all_comments(self) -> List[Dict[str, Any]]:
        """Get comments from all platforms"""
        all_comments = []
        
        for platform, parser in self.parsers.items():
            if isinstance(parser, SocialMediaParser):
                comments = await parser.get_comments()
                all_comments.extend(comments)
        
        return all_comments
    
    async def post_reply_all(self, message_id: str, text: str, platform: str) -> bool:
        """Post reply to a specific platform"""
        parser = self.parsers.get(platform)
        if parser and isinstance(parser, SocialMediaParser):
            return await parser.post_reply(message_id, text)
        return False 