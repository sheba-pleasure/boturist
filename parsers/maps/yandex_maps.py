from playwright.async_api import async_playwright
from typing import Dict, List, Optional
import logging
import json
from datetime import datetime
from celery import shared_task

logger = logging.getLogger(__name__)

class YandexMapsParser:
    async def __init__(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        
    async def close(self):
        """Close browser and playwright"""
        await self.browser.close()
        await self.playwright.stop()
    
    async def get_reviews(self, business_url: str) -> List[Dict]:
        """Get reviews for a business from Yandex Maps"""
        try:
            page = await self.browser.new_page()
            await page.goto(business_url)
            
            # Wait for reviews to load
            await page.wait_for_selector('.business-reviews-card')
            
            # Extract reviews
            reviews = await page.evaluate('''() => {
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
            }''')
            
            await page.close()
            return reviews
            
        except Exception as e:
            logger.error(f"Error parsing Yandex Maps: {e}")
            return []

@shared_task
async def parse_yandex_maps_reviews(business_url: str) -> None:
    """Celery task to parse Yandex Maps reviews"""
    parser = await YandexMapsParser()
    try:
        reviews = await parser.get_reviews(business_url)
        await save_reviews_to_mongodb(reviews, business_url)
    finally:
        await parser.close()

async def save_reviews_to_mongodb(reviews: List[Dict], business_url: str) -> None:
    """Save parsed reviews to MongoDB"""
    from pymongo import MongoClient
    from django.conf import settings
    
    client = MongoClient(settings.MONGODB_URI)
    db = client.maps_data
    
    # Save reviews
    db.yandex_reviews.update_one(
        {'business_url': business_url},
        {
            '$set': {
                'reviews': reviews,
                'updated_at': datetime.utcnow()
            }
        },
        upsert=True
    ) 