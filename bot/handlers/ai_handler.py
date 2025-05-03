from typing import Dict, Optional
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from bot.ml.ai_assistant import AIAssistant, ModelType
from django.conf import settings
from web.admin_panel.models import TelegramUser, BotSettings

logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        self.assistant = AIAssistant(
            model_type=ModelType(settings.DEFAULT_AI_MODEL)
        )
        self.max_message_length = 2000
        self.user_cooldowns = {}
        self.cooldown_seconds = 5  # Минимальный интервал между запросами
        self.admin_ids = settings.BOT_ADMIN_IDS  # Список ID администраторов

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming message and generate AI response"""
        if not update.message or not update.message.text:
            return

        # Проверяем, включен ли ИИ-помощник
        bot_settings = BotSettings.get_settings()
        if not bot_settings.ai_assistant_enabled:
            await update.message.reply_text(
                "Извините, ИИ-помощник временно отключен. "
                "Пожалуйста, воспользуйтесь другими функциями бота или попробуйте позже."
            )
            return

        user_id = update.effective_user.id
        message_text = update.message.text

        # Проверяем длину сообщения
        if len(message_text) > self.max_message_length:
            await update.message.reply_text(
                "Извините, ваше сообщение слишком длинное. "
                f"Максимальная длина: {self.max_message_length} символов."
            )
            return

        # Проверяем cooldown
        if not self._check_cooldown(user_id):
            await update.message.reply_text(
                f"Пожалуйста, подождите {self.cooldown_seconds} секунд между запросами."
            )
            return

        try:
            # Отправляем индикатор набора текста
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )

            # Получаем ответ от модели
            response = await self.assistant.get_response(message_text)

            # Отправляем ответ
            await update.message.reply_text(response)

            # Логируем взаимодействие
            await self.assistant.log_interaction(
                user_id=user_id,
                message=message_text,
                response=response
            )

        except Exception as e:
            logger.error(f"Error in AI handler: {str(e)}")
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке вашего запроса. "
                "Пожалуйста, попробуйте позже."
            )

    async def toggle_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Toggle AI assistant state (admin only)"""
        user_id = update.effective_user.id
        
        # Проверяем, является ли пользователь администратором
        if user_id not in self.admin_ids:
            await update.message.reply_text(
                "У вас нет прав для выполнения этой команды."
            )
            return

        # Переключаем состояние ИИ-помощника
        settings = BotSettings.get_settings()
        settings.ai_assistant_enabled = not settings.ai_assistant_enabled
        settings.save()

        # Создаем клавиатуру для управления
        keyboard = [[
            InlineKeyboardButton(
                "✅ Включить" if not settings.ai_assistant_enabled else "❌ Отключить",
                callback_data="toggle_ai"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"ИИ-помощник {'включен' if settings.ai_assistant_enabled else 'отключен'}.",
            reply_markup=reply_markup
        )

    async def handle_toggle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle toggle button callback"""
        query = update.callback_query
        user_id = query.from_user.id

        if user_id not in self.admin_ids:
            await query.answer("У вас нет прав для выполнения этой команды.")
            return

        settings = BotSettings.get_settings()
        settings.ai_assistant_enabled = not settings.ai_assistant_enabled
        settings.save()

        # Обновляем клавиатуру
        keyboard = [[
            InlineKeyboardButton(
                "✅ Включить" if not settings.ai_assistant_enabled else "❌ Отключить",
                callback_data="toggle_ai"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"ИИ-помощник {'включен' if settings.ai_assistant_enabled else 'отключен'}.",
            reply_markup=reply_markup
        )
        await query.answer()

    def _check_cooldown(self, user_id: int) -> bool:
        """Check if user can make a new request"""
        from time import time

        current_time = time()
        last_request = self.user_cooldowns.get(user_id, 0)

        if current_time - last_request < self.cooldown_seconds:
            return False

        self.user_cooldowns[user_id] = current_time
        return True

def setup_ai_handlers(application):
    """Setup AI-related handlers"""
    ai_handler = AIHandler()
    
    # Обработчик текстовых сообщений
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ai_handler.handle_message
        )
    )
    
    # Команда для переключения состояния ИИ-помощника
    application.add_handler(
        CommandHandler(
            "toggle_ai",
            ai_handler.toggle_ai
        )
    )
    
    # Обработчик callback для кнопки переключения
    application.add_handler(
        CallbackQueryHandler(
            ai_handler.handle_toggle_callback,
            pattern="^toggle_ai$"
        )
    ) 