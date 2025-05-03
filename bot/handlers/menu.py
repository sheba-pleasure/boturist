from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from typing import List, Dict
import json
import logging
from datetime import datetime
from bot.ml.categorizer import categorize_message
from bot.mailing.sender import send_category_materials
from bot.storage.materials import MaterialManager

logger = logging.getLogger(__name__)

# Main menu keyboard
MAIN_MENU = ReplyKeyboardMarkup([
    ['📚 Материалы', '❓ Консультация'],
    ['📊 Мои заявки', '⚙️ Настройки']
], resize_keyboard=True)

# Materials submenu keyboard
MATERIALS_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 Чек-листы", callback_data='materials_checklists')],
    [InlineKeyboardButton("📖 Инструкции", callback_data='materials_instructions')],
    [InlineKeyboardButton("📑 Документы", callback_data='materials_documents')],
    [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
])

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main menu"""
    await update.message.reply_text(
        "Выберите раздел:",
        reply_markup=MAIN_MENU
    )

async def handle_materials_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle materials menu selection"""
    await update.message.reply_text(
        "Выберите тип материалов:",
        reply_markup=MATERIALS_MENU
    )

async def handle_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle consultation request"""
    # Create consultation request buttons
    keyboard = [
        [InlineKeyboardButton("🤝 Связаться с юристом", callback_data='contact_lawyer')],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data='create_request')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Как мы можем вам помочь?",
        reply_markup=reply_markup
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('materials_'):
        category = query.data.replace('materials_', '')
        material_manager = MaterialManager()
        materials = await material_manager.get_materials_by_category(category)
        
        if materials:
            # Create buttons for each material
            keyboard = []
            for material in materials[:5]:  # Show top 5 materials
                keyboard.append([InlineKeyboardButton(
                    material['title'],
                    callback_data=f"material_{material['id']}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='materials_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                f"Доступные материалы по теме {category}:",
                reply_markup=reply_markup
            )
        else:
            await query.message.edit_text(
                "К сожалению, материалы не найдены.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='materials_menu')
                ]])
            )
    
    elif query.data.startswith('material_'):
        material_id = query.data.replace('material_', '')
        # Schedule material sending
        await send_category_materials(update.effective_chat.id, material_id)
        
        await query.message.edit_text(
            "Материал отправлен! Проверьте сообщения.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='materials_menu')
            ]])
        )
    
    elif query.data == 'contact_lawyer':
        # Create consultation request
        keyboard = [
            [InlineKeyboardButton("📞 Телефон", callback_data='contact_phone')],
            [InlineKeyboardButton("💬 Чат", callback_data='contact_chat')],
            [InlineKeyboardButton("🔙 Назад", callback_data='consultation_menu')]
        ]
        await query.message.edit_text(
            "Выберите способ связи с юристом:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == 'create_request':
        context.user_data['awaiting_request'] = True
        await query.message.edit_text(
            "Опишите ваш вопрос или проблему. Я помогу направить его нужному специалисту.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Отмена", callback_data='cancel_request')
            ]])
        )

async def handle_request_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming request message"""
    if context.user_data.get('awaiting_request'):
        # Categorize message
        category_info = await categorize_message(update.message.text)
        
        # Save request to database
        request_id = await save_request(
            user_id=update.effective_user.id,
            text=update.message.text,
            category=category_info['category']
        )
        
        # Send confirmation
        await update.message.reply_text(
            f"Ваша заявка #{request_id} принята!\n"
            f"Категория: {category_info['category_name']}\n\n"
            "Специалист свяжется с вами в ближайшее время.",
            reply_markup=MAIN_MENU
        )
        
        # Send relevant materials
        await send_category_materials(update.effective_chat.id, category_info['category'])
        
        # Clear awaiting flag
        context.user_data['awaiting_request'] = False

async def save_request(user_id: int, text: str, category: str) -> str:
    """Save request to MongoDB"""
    from pymongo import MongoClient
    from django.conf import settings
    from bson.objectid import ObjectId
    
    client = MongoClient(settings.MONGODB_URI)
    db = client.bot_data
    
    result = db.requests.insert_one({
        'user_id': user_id,
        'text': text,
        'category': category,
        'status': 'new',
        'created_at': datetime.utcnow()
    })
    
    return str(result.inserted_id) 