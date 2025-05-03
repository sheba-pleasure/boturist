from typing import Dict, List, Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import logging
from datetime import datetime
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

class LawyerNotifier:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def notify_new_request(self, request_data: Dict, lawyer_id: int) -> bool:
        """Send notification about new request to lawyer"""
        try:
            # Create detailed message
            message = (
                f"🆕 Новая заявка #{request_data['id']}\n\n"
                f"👤 Клиент: {request_data['client_name']}\n"
                f"📝 Категория: {request_data['category']}\n"
                f"📅 Дата: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"💬 Текст заявки:\n{request_data['text']}"
            )
            
            # Create action buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Принять", callback_data=f"accept_request_{request_data['id']}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_request_{request_data['id']}")
                ],
                [InlineKeyboardButton("📞 Связаться с клиентом", callback_data=f"contact_client_{request_data['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send notification
            await self.bot.send_message(
                chat_id=lawyer_id,
                text=message,
                reply_markup=reply_markup
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification to lawyer {lawyer_id}: {e}")
            return False
    
    async def notify_request_update(self, request_id: str, status: str, 
                                  lawyer_id: int, comment: Optional[str] = None) -> bool:
        """Send notification about request status update"""
        try:
            message = f"📝 Обновление заявки #{request_id}\n\nСтатус изменен на: {status}"
            if comment:
                message += f"\n\nКомментарий: {comment}"
            
            await self.bot.send_message(
                chat_id=lawyer_id,
                text=message
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending update notification to lawyer {lawyer_id}: {e}")
            return False

async def get_available_lawyers(category: str) -> List[Dict]:
    """Get list of available lawyers for category"""
    from pymongo import MongoClient
    
    client = MongoClient(settings.MONGODB_URI)
    db = client.bot_data
    
    return list(db.lawyers.find({
        'categories': category,
        'is_available': True
    }))

@shared_task
async def distribute_request(request_id: str) -> None:
    """Distribute request to available lawyers"""
    from pymongo import MongoClient
    from bson.objectid import ObjectId
    import telegram
    
    try:
        client = MongoClient(settings.MONGODB_URI)
        db = client.bot_data
        
        # Get request data
        request = db.requests.find_one({'_id': ObjectId(request_id)})
        if not request:
            logger.error(f"Request {request_id} not found")
            return
        
        # Get user data
        user = db.users.find_one({'user_id': request['user_id']})
        
        # Prepare request data for notification
        request_data = {
            'id': str(request['_id']),
            'client_name': f"{user['first_name']} {user.get('last_name', '')}",
            'category': request['category'],
            'text': request['text']
        }
        
        # Get available lawyers
        lawyers = await get_available_lawyers(request['category'])
        
        if not lawyers:
            logger.warning(f"No available lawyers found for category {request['category']}")
            return
        
        # Initialize bot
        bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
        notifier = LawyerNotifier(bot)
        
        # Notify lawyers
        for lawyer in lawyers:
            await notifier.notify_new_request(request_data, lawyer['telegram_id'])
        
        # Update request status
        db.requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {
                'status': 'distributed',
                'distributed_at': datetime.utcnow(),
                'distributed_to': [str(l['_id']) for l in lawyers]
            }}
        )
        
    except Exception as e:
        logger.error(f"Error distributing request {request_id}: {e}")

@shared_task
async def handle_lawyer_response(request_id: str, lawyer_id: int, 
                               action: str, comment: Optional[str] = None) -> None:
    """Handle lawyer's response to request"""
    from pymongo import MongoClient
    from bson.objectid import ObjectId
    import telegram
    
    try:
        client = MongoClient(settings.MONGODB_URI)
        db = client.bot_data
        
        # Update request status
        new_status = 'accepted' if action == 'accept' else 'declined'
        db.requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {
                'status': new_status,
                'assigned_to': lawyer_id if action == 'accept' else None,
                'updated_at': datetime.utcnow(),
                'comment': comment
            }}
        )
        
        # Notify other lawyers if request was accepted
        if action == 'accept':
            bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
            notifier = LawyerNotifier(bot)
            
            request = db.requests.find_one({'_id': ObjectId(request_id)})
            for distributed_lawyer_id in request.get('distributed_to', []):
                if str(distributed_lawyer_id) != str(lawyer_id):
                    await notifier.notify_request_update(
                        request_id,
                        "Заявка принята другим юристом",
                        int(distributed_lawyer_id)
                    )
        
    except Exception as e:
        logger.error(f"Error handling lawyer response for request {request_id}: {e}") 