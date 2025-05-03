import asyncio
import logging
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
import os

from database import Database
from content import RequestFileManager
from handlers.ai_handler import setup_ai_handlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class BotHub:
    def __init__(self):
        """Initialize the bot hub with necessary components"""
        self.application = Application.builder().token(TOKEN).build()
        self.db = Database()
        self.file_manager = RequestFileManager(self.db)
        self.setup_handlers()
        self.active_requests = {}  # Store active request IDs for users

    def setup_handlers(self):
        """Setup message and command handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Setup AI handlers
        setup_ai_handlers(self.application)
        
        # Message handlers for requests
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(r"^/request") & ~filters.COMMAND,
                self.handle_message
            )
        )
        self.application.add_handler(
            MessageHandler(
                filters.Document.ALL | filters.PHOTO | filters.VIDEO,
                self.handle_file
            )
        )
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        keyboard = [
            [
                InlineKeyboardButton("📝 Оставить заявку", callback_data="new_request"),
                InlineKeyboardButton("🤖 ИИ-помощник", callback_data="ai_help"),
            ],
            [
                InlineKeyboardButton("📚 Материалы", callback_data="materials"),
                InlineKeyboardButton("❓ Помощь", callback_data="help"),
            ],
            [
                InlineKeyboardButton("📞 Контакты", callback_data="contacts"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Добро пожаловать! Я ваш персональный помощник.\n\n"
            "Чем могу помочь?\n\n"
            "💡 Вы можете общаться со мной напрямую - я использую ИИ для ответов на ваши вопросы.\n"
            "Для специальных запросов используйте команду /request.",
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_text = (
            "🔍 Доступные команды:\n\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/request - Создать новую заявку\n"
            "/model - Выбрать модель ИИ\n\n"
            "Также вы можете:\n"
            "- Общаться с ИИ-помощником напрямую\n"
            "- Оставить заявку\n"
            "- Получить полезные материалы\n"
            "- Связаться с нами\n"
        )
        await update.message.reply_text(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Check if this is part of an active request
        if user_id in self.active_requests:
            # Create new request if not exists
            if self.active_requests[user_id] is None:
                request_id = await self.db.create_request(
                    user_id=user_id,
                    category="general",
                    message=message_text
                )
                self.active_requests[user_id] = request_id
                
                await update.message.reply_text(
                    "✅ Ваша заявка создана!\n\n"
                    "Вы можете прикрепить дополнительные файлы к заявке.\n"
                    "Когда закончите, нажмите /done для завершения заявки.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Завершить заявку", callback_data="finish_request")
                    ]])
                )
            else:
                # Update existing request
                # Here you would typically append the message to the request
                await update.message.reply_text(
                    "✅ Сообщение добавлено к заявке.\n"
                    "Вы можете продолжать добавлять сообщения и файлы."
                )
        else:
            await update.message.reply_text(
                "Для создания новой заявки, пожалуйста, используйте команду /start"
            )

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads"""
        user_id = update.effective_user.id
        
        if user_id not in self.active_requests or self.active_requests[user_id] is None:
            await update.message.reply_text(
                "⚠️ Пожалуйста, сначала создайте заявку с помощью текстового описания."
            )
            return
        
        request_id = self.active_requests[user_id]
        
        try:
            # Handle different types of files
            if update.message.document:
                file = update.message.document
            elif update.message.photo:
                file = update.message.photo[-1]  # Get the highest quality photo
            elif update.message.video:
                file = update.message.video
            else:
                await update.message.reply_text("❌ Этот тип файла не поддерживается.")
                return
            
            # Save file
            try:
                file_info = await self.file_manager.save_file(request_id, file)
                
                if file_info:
                    # Создаем клавиатуру с кнопкой удаления
                    keyboard = [[
                        InlineKeyboardButton(
                            "🗑 Удалить файл",
                            callback_data=f"delete_file_{file_info['id']}"
                        )
                    ]]
                    
                    # Для изображений добавляем предпросмотр
                    if file_info.get('preview_key'):
                        urls = await self.file_manager.get_file_url(file_info['id'], preview=True)
                        if urls and urls.get('preview_url'):
                            await update.message.reply_photo(
                                photo=urls['preview_url'],
                                caption=f"✅ Файл {file_info['file_name']} успешно прикреплен к заявке.",
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                            return
                    
                    # Для остальных файлов просто сообщение
                    await update.message.reply_text(
                        f"✅ Файл {file_info['file_name']} успешно прикреплен к заявке.\n"
                        f"Размер: {self._format_size(file_info['file_size'])}\n"
                        "Вы можете продолжать добавлять файлы или нажать 'Завершить заявку'.",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        "❌ Произошла ошибка при сохранении файла. Пожалуйста, попробуйте еще раз."
                    )
            
            except ValueError as e:
                await update.message.reply_text(f"⚠️ {str(e)}")
                
        except Exception as e:
            logger.error(f"Error handling file: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке файла. Пожалуйста, попробуйте еще раз."
            )

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} ТБ"

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "new_request":
            await self.handle_new_request(query)
        elif query.data == "materials":
            await self.handle_materials(query)
        elif query.data == "help":
            await self.handle_help(query)
        elif query.data == "contacts":
            await self.handle_contacts(query)
        elif query.data == "finish_request":
            await self.finish_request(query)
        elif query.data.startswith("delete_file_"):
            await self.delete_file(query)

    async def handle_new_request(self, query):
        """Handle new request creation"""
        user_id = query.from_user.id
        self.active_requests[user_id] = None  # Will be set when request is created
        
        await query.message.reply_text(
            "📝 Для создания заявки, пожалуйста, опишите ваш вопрос или проблему.\n"
            "Вы также можете прикрепить файлы (документы, фото, видео) к заявке.\n"
            "Я помогу вам связаться с нужным специалистом."
        )

    async def handle_materials(self, query):
        """Handle materials section"""
        keyboard = [
            [
                InlineKeyboardButton("📋 Чек-листы", callback_data="materials_checklists"),
                InlineKeyboardButton("📖 Гайды", callback_data="materials_guides"),
            ],
            [
                InlineKeyboardButton("📄 Документы", callback_data="materials_docs"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "📚 Выберите категорию материалов:",
            reply_markup=reply_markup
        )

    async def handle_help(self, query):
        """Handle help section"""
        await query.message.edit_text(
            "❓ Часто задаваемые вопросы:\n\n"
            "1. Как оставить заявку?\n"
            "2. Как получить консультацию?\n"
            "3. Какие документы нужны?\n\n"
            "Выберите интересующий вас вопрос или напишите свой."
        )

    async def handle_contacts(self, query):
        """Handle contacts section"""
        await query.message.edit_text(
            "📞 Наши контакты:\n\n"
            "📱 Телефон: +7 (XXX) XXX-XX-XX\n"
            "📧 Email: contact@example.com\n"
            "🌐 Сайт: www.example.com\n\n"
            "Время работы: Пн-Пт, 9:00-18:00"
        )

    async def finish_request(self, query):
        """Finish and close the request"""
        user_id = query.from_user.id
        
        if user_id in self.active_requests:
            request_id = self.active_requests[user_id]
            # Here you would typically update the request status in database
            del self.active_requests[user_id]
            
            await query.message.edit_text(
                "✅ Ваша заявка успешно создана и отправлена!\n"
                "Мы свяжемся с вами в ближайшее время.\n\n"
                "Вы можете создать новую заявку с помощью команды /start"
            )
        else:
            await query.message.edit_text(
                "⚠️ У вас нет активных заявок.\n"
                "Используйте /start для создания новой заявки."
            )

    async def delete_file(self, query):
        """Handle file deletion"""
        try:
            file_id = int(query.data.split('_')[-1])
            
            # Проверяем, что файл принадлежит текущему пользователю
            user_id = query.from_user.id
            if user_id not in self.active_requests:
                await query.message.edit_text("⚠️ У вас нет активных заявок.")
                return
            
            # Удаляем файл
            if await self.file_manager.delete_file(file_id):
                await query.message.edit_text(
                    "✅ Файл успешно удален из заявки.",
                    reply_markup=None
                )
            else:
                await query.message.edit_text(
                    "❌ Не удалось удалить файл. Пожалуйста, попробуйте позже.",
                    reply_markup=None
                )
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            await query.message.edit_text(
                "❌ Произошла ошибка при удалении файла.",
                reply_markup=None
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Error occurred: {context.error}")
        if update:
            await update.message.reply_text(
                "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            )

    def run(self):
        """Run the bot"""
        self.application.run_polling()

def main():
    """Main function"""
    bot = BotHub()
    bot.run()

if __name__ == "__main__":
    main() 