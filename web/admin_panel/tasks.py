from celery import shared_task
from django.utils import timezone
from django.conf import settings
import telegram
import vk_api
from .models import Publication, Campaign, RequestFromPost
import logging
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from bot.ml.categorizer import MessageCategorizer
from typing import Optional

logger = logging.getLogger(__name__)

@shared_task
def process_scheduled_publications():
    """Process all scheduled publications that are due"""
    now = timezone.now()
    publications = Publication.objects.filter(
        status='scheduled',
        scheduled_time__lte=now
    )

    for publication in publications:
        try:
            # Send to each selected channel
            for channel in publication.channels:
                if channel == 'telegram':
                    send_to_telegram.delay(publication.id)
                elif channel == 'vk':
                    send_to_vk.delay(publication.id)
                elif channel == 'facebook':
                    send_to_facebook.delay(publication.id)
                elif channel == 'instagram':
                    send_to_instagram.delay(publication.id)

            publication.status = 'published'
            publication.save()
            
        except Exception as e:
            logger.error(f"Error processing publication {publication.id}: {e}")
            publication.status = 'failed'
            publication.save()

@shared_task
def send_to_telegram(publication_id):
    """Send publication to Telegram channel"""
    try:
        publication = Publication.objects.get(id=publication_id)
        bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
        
        message = f"{publication.title}\n\n{publication.content}"
        
        # If there's an attached material, add its link
        if publication.material:
            message += f"\n\nПодробнее: {publication.material.file.url}"
        
        # Send message with preview disabled for URLs
        bot.send_message(
            chat_id=settings.TELEGRAM_CHANNEL_ID,
            text=message,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        # If there's a file, send it separately
        if publication.material and publication.material.file:
            bot.send_document(
                chat_id=settings.TELEGRAM_CHANNEL_ID,
                document=publication.material.file.file
            )
        
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")
        raise

@shared_task
def send_to_vk(publication_id):
    """Send publication to VK group"""
    try:
        publication = Publication.objects.get(id=publication_id)
        vk_session = vk_api.VkApi(token=settings.VK_TOKEN)
        vk = vk_session.get_api()
        
        post = {
            'message': f"{publication.title}\n\n{publication.content}",
            'owner_id': f"-{settings.VK_GROUP_ID}"  # Negative ID for groups
        }
        
        # If there's an attached material, upload and attach it
        if publication.material and publication.material.file:
            upload = vk_api.VkUpload(vk_session)
            if publication.material.file.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                photo = upload.photo(
                    publication.material.file.file,
                    group_id=settings.VK_GROUP_ID
                )
                post['attachments'] = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
            else:
                doc = upload.document(
                    publication.material.file.file,
                    group_id=settings.VK_GROUP_ID
                )
                post['attachments'] = f"doc{doc['doc']['owner_id']}_{doc['doc']['id']}"
        
        vk.wall.post(**post)
        
    except Exception as e:
        logger.error(f"Error sending to VK: {e}")
        raise

@shared_task
def update_campaign_metrics():
    """Update metrics for active campaigns"""
    campaigns = Campaign.objects.filter(status='active')
    
    for campaign in campaigns:
        try:
            metrics = {
                'total_impressions': 0,
                'total_clicks': 0,
                'total_conversions': 0,
                'channels': {}
            }
            
            # Collect metrics from different sources
            if 'telegram' in campaign.channels:
                telegram_metrics = get_telegram_metrics(campaign)
                metrics['channels']['telegram'] = telegram_metrics
                metrics['total_impressions'] += telegram_metrics.get('views', 0)
                metrics['total_clicks'] += telegram_metrics.get('clicks', 0)
            
            if 'vk' in campaign.channels:
                vk_metrics = get_vk_metrics(campaign)
                metrics['channels']['vk'] = vk_metrics
                metrics['total_impressions'] += vk_metrics.get('views', 0)
                metrics['total_clicks'] += vk_metrics.get('clicks', 0)
            
            # Calculate conversion rate
            if metrics['total_impressions'] > 0:
                metrics['conversion_rate'] = (
                    metrics['total_conversions'] / metrics['total_impressions']
                ) * 100
            
            # Update campaign metrics
            campaign.metrics = metrics
            campaign.save()
            
        except Exception as e:
            logger.error(f"Error updating metrics for campaign {campaign.id}: {e}")

@shared_task
def process_post_requests():
    """Process requests from social media posts"""
    # Get unprocessed requests
    requests = RequestFromPost.objects.filter(status='new')
    
    for request in requests:
        try:
            # Analyze request content
            category = analyze_request_content(request.content)
            
            # Find available lawyer
            lawyer = find_available_lawyer(category)
            
            if lawyer:
                request.assigned_to = lawyer
                request.status = 'processing'
            else:
                request.status = 'pending'
            
            request.save()
            
        except Exception as e:
            logger.error(f"Error processing request {request.id}: {e}")

def get_telegram_metrics(campaign):
    """Get metrics from Telegram channel"""
    try:
        bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
        
        # Get channel info
        chat = bot.get_chat(settings.TELEGRAM_CHANNEL_ID)
        
        # Get message statistics
        messages = bot.get_chat_history(
            chat_id=settings.TELEGRAM_CHANNEL_ID,
            limit=100  # Adjust as needed
        )
        
        total_views = 0
        total_forwards = 0
        
        for message in messages:
            if hasattr(message, 'views'):
                total_views += message.views
            if hasattr(message, 'forward_count'):
                total_forwards += message.forward_count
        
        return {
            'subscribers': chat.member_count,
            'views': total_views,
            'forwards': total_forwards,
            'engagement_rate': (total_forwards / total_views * 100) if total_views > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting Telegram metrics: {e}")
        return {}

def get_vk_metrics(campaign):
    """Get metrics from VK group"""
    try:
        vk_session = vk_api.VkApi(token=settings.VK_TOKEN)
        vk = vk_session.get_api()
        
        # Get group statistics
        stats = vk.stats.get(
            group_id=settings.VK_GROUP_ID,
            intervals_count=30,  # Last 30 days
            stats_groups=['visitors', 'reach', 'activity']
        )
        
        total_views = sum(day.get('views', 0) for day in stats)
        total_clicks = sum(day.get('clicks', 0) for day in stats)
        total_likes = sum(day.get('likes', 0) for day in stats)
        total_reposts = sum(day.get('reposts', 0) for day in stats)
        
        return {
            'views': total_views,
            'clicks': total_clicks,
            'likes': total_likes,
            'reposts': total_reposts,
            'engagement_rate': (
                (total_likes + total_reposts) / total_views * 100
            ) if total_views > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting VK metrics: {e}")
        return {}

@shared_task
def send_to_facebook(publication_id):
    """Send publication to Facebook page"""
    try:
        publication = Publication.objects.get(id=publication_id)
        # TODO: Implement Facebook API integration
        logger.info(f"Facebook publication scheduled: {publication_id}")
    except Exception as e:
        logger.error(f"Error sending to Facebook: {e}")
        raise

@shared_task
def send_to_instagram(publication_id):
    """Send publication to Instagram account"""
    try:
        publication = Publication.objects.get(id=publication_id)
        # TODO: Implement Instagram API integration
        logger.info(f"Instagram publication scheduled: {publication_id}")
    except Exception as e:
        logger.error(f"Error sending to Instagram: {e}")
        raise

def analyze_request_content(content: str) -> str:
    """Analyze request content and determine category"""
    categorizer = MessageCategorizer()
    category, probability = categorizer.predict(content)
    return category

def find_available_lawyer(category: str) -> Optional[User]:
    """Find available lawyer for given category"""
    try:
        # Get lawyers who handle this category and are available
        lawyers = User.objects.filter(
            groups__name='lawyers',
            lawyer_profile__categories__contains=[category],
            lawyer_profile__is_available=True
        ).order_by('lawyer_profile__active_cases')
        
        return lawyers.first() if lawyers.exists() else None
        
    except Exception as e:
        logger.error(f"Error finding lawyer for category {category}: {e}")
        return None 