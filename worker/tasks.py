import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

from celery import Celery
from celery.schedules import crontab

from bot.config import Config
from bot.database import Database
from bot.social_media import SocialMediaHub
from bot.content import ContentScheduler
from bot.analytics import Analytics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery('tasks')
celery_app.conf.update(
    broker_url=Config.get_redis_url(),
    result_backend=Config.get_redis_url(),
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)

# Initialize services
db = Database()
social_media = SocialMediaHub()
content_scheduler = ContentScheduler(db)
analytics = Analytics(db)

@celery_app.task
def fetch_social_media_messages():
    """Fetch messages from all social media platforms"""
    async def _fetch():
        try:
            # Connect to database
            await db.connect()
            
            # Fetch messages
            messages = await social_media.get_all_messages()
            
            # Process each message
            for message in messages:
                # Store in database
                user_id = await db.get_or_create_user({
                    'telegram_id': message['from_id'],
                    'platform': message['platform']
                })
                
                await db.create_request(
                    user_id=user_id,
                    category='social_media',
                    message=message['text']
                )
                
                # Track analytics
                await analytics.track_message(
                    platform=message['platform'],
                    message_type='incoming'
                )
            
            return len(messages)
            
        except Exception as e:
            logger.error(f"Error fetching social media messages: {e}")
            await analytics.track_error('social_media_fetch', e)
            return 0
            
        finally:
            await db.close()
    
    return asyncio.run(_fetch())

@celery_app.task
def publish_scheduled_content():
    """Publish scheduled content to social media"""
    async def _publish():
        try:
            # Connect to database
            await db.connect()
            
            # Get pending posts
            posts = await content_scheduler.get_pending_posts()
            published_count = 0
            
            # Publish each post
            for post in posts:
                success = await social_media.post_reply_all(
                    message_id=None,
                    text=post['content'],
                    platform=post['platform']
                )
                
                if success:
                    await content_scheduler.mark_post_published(post['id'])
                    published_count += 1
                    
                    await analytics.track_message(
                        platform=post['platform'],
                        message_type='outgoing'
                    )
            
            return published_count
            
        except Exception as e:
            logger.error(f"Error publishing scheduled content: {e}")
            await analytics.track_error('content_publish', e)
            return 0
            
        finally:
            await db.close()
    
    return asyncio.run(_publish())

@celery_app.task
def generate_daily_report():
    """Generate daily analytics report"""
    async def _generate():
        try:
            # Connect to database
            await db.connect()
            
            # Get yesterday's date
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            # Get statistics
            stats = await analytics.get_daily_stats(yesterday)
            
            # Store report in database
            async with db.pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO daily_reports (
                        date, total_messages, platform_stats,
                        error_count, created_at
                    )
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    """,
                    yesterday.date(),
                    stats['total_messages'],
                    stats['platform_stats'],
                    stats['error_count']
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            await analytics.track_error('report_generation', e)
            return None
            
        finally:
            await db.close()
    
    return asyncio.run(_generate())

@celery_app.task
def cleanup_old_data():
    """Clean up old data from database"""
    async def _cleanup():
        try:
            # Connect to database
            await db.connect()
            
            # Calculate cutoff date (30 days ago)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            async with db.pg_pool.acquire() as conn:
                # Delete old analytics data
                await conn.execute(
                    """
                    DELETE FROM analytics
                    WHERE timestamp < $1
                    """,
                    cutoff_date
                )
                
                # Delete old scheduled posts
                await conn.execute(
                    """
                    DELETE FROM scheduled_posts
                    WHERE status = 'published'
                    AND published_at < $1
                    """,
                    cutoff_date
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            await analytics.track_error('data_cleanup', e)
            return False
            
        finally:
            await db.close()
    
    return asyncio.run(_cleanup())

# Schedule periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Fetch social media messages every 5 minutes
    sender.add_periodic_task(
        300.0,
        fetch_social_media_messages.s(),
        name='fetch_social_media_messages'
    )
    
    # Check and publish scheduled content every minute
    sender.add_periodic_task(
        60.0,
        publish_scheduled_content.s(),
        name='publish_scheduled_content'
    )
    
    # Generate daily report at 00:01 UTC
    sender.add_periodic_task(
        crontab(hour=0, minute=1),
        generate_daily_report.s(),
        name='generate_daily_report'
    )
    
    # Clean up old data weekly
    sender.add_periodic_task(
        crontab(day_of_week='sunday', hour=1, minute=0),
        cleanup_old_data.s(),
        name='cleanup_old_data'
    ) 