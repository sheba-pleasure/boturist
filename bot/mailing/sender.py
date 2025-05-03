from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from celery import shared_task
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from django.conf import settings
from bot.storage.materials import MaterialManager
from web.admin_panel.models import TelegramUser

logger = logging.getLogger(__name__)

class MailingSender:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.material_manager = MaterialManager()

    async def send_material(self, chat_id: int, material_id: str) -> bool:
        """Send specific material to user"""
        try:
            material = await self.material_manager.get_material(material_id)
            if not material:
                return False

            # Create inline keyboard with buttons
            keyboard = [
                [InlineKeyboardButton("Подробнее", callback_data=f"material_{material_id}")],
                [InlineKeyboardButton("Скачать PDF", url=material['file_url'])]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send message with material preview
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"📚 {material['title']}\n\n{material['description']}",
                reply_markup=reply_markup
            )

            # Log successful sending
            await self._log_sending(chat_id, material_id)
            return True

        except Exception as e:
            logger.error(f"Error sending material {material_id} to {chat_id}: {e}")
            return False

    async def _log_sending(self, chat_id: int, material_id: str) -> None:
        """Log material sending to MongoDB"""
        from pymongo import MongoClient

        client = MongoClient(settings.MONGODB_URI)
        db = client.bot_data

        db.material_sendings.insert_one({
            'chat_id': chat_id,
            'material_id': material_id,
            'sent_at': datetime.utcnow()
        })

@shared_task
async def schedule_mailing(material_id: str, user_filter: Dict = None) -> None:
    """Schedule mailing of material to filtered users"""
    from web.admin_panel.models import TelegramUser
    from django.conf import settings
    import telegram

    bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
    sender = MailingSender(bot)

    # Get users matching filter
    users = TelegramUser.objects.filter(**user_filter) if user_filter else TelegramUser.objects.all()

    for user in users:
        try:
            # Add random delay to avoid flooding
            await asyncio.sleep(1)
            await sender.send_material(user.telegram_id, material_id)
        except Exception as e:
            logger.error(f"Error in scheduled mailing for user {user.telegram_id}: {e}")

@shared_task
async def send_welcome_materials(chat_id: int) -> None:
    """Send welcome pack of materials to new user"""
    from django.conf import settings
    import telegram

    bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
    sender = MailingSender(bot)

    # Get welcome materials IDs
    welcome_materials = await sender.material_manager.get_materials_by_tag('welcome')
    
    for material in welcome_materials:
        try:
            await asyncio.sleep(1)  # Delay between messages
            await sender.send_material(chat_id, material['id'])
        except Exception as e:
            logger.error(f"Error sending welcome material to {chat_id}: {e}")

@shared_task
async def send_category_materials(chat_id: int, category: str) -> None:
    """Send materials based on user's query category"""
    from django.conf import settings
    import telegram

    bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
    sender = MailingSender(bot)

    # Get relevant materials
    materials = await sender.material_manager.get_materials_by_category(category)
    
    for material in materials[:3]:  # Send top 3 most relevant materials
        try:
            await asyncio.sleep(1)
            await sender.send_material(chat_id, material['id'])
        except Exception as e:
            logger.error(f"Error sending category material to {chat_id}: {e}") 