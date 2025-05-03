import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers import start_command, help_command, settings_command
from bot.utils import get_user_settings, update_user_settings

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
class TestTelegramBot:
    @pytest.fixture
    def mock_update(self):
        update = AsyncMock(spec=Update)
        update.effective_chat.id = 123456789
        update.message.text = "Hello, bot!"
        return update

    @pytest.fixture
    def mock_context(self):
        context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        return context

    async def test_start_command(self, mock_update, mock_context):
        """Test the /start command"""
        from bot.handlers.commands import start_command
        
        await start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args, _ = mock_update.message.reply_text.call_args
        assert "Welcome" in args[0]

    async def test_help_command(self, mock_update, mock_context):
        """Test the /help command"""
        from bot.handlers.commands import help_command
        
        await help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args, _ = mock_update.message.reply_text.call_args
        assert "Available commands" in args[0]

    @pytest.mark.parametrize("user_message,expected_response", [
        ("Hello", "Hi there!"),
        ("How are you?", "I'm doing great, thanks for asking!"),
        ("Bye", "Goodbye! Have a great day!"),
    ])
    async def test_message_handler(self, mock_update, mock_context, user_message, expected_response):
        """Test message handler with different inputs"""
        from bot.handlers.messages import message_handler
        
        mock_update.message.text = user_message
        
        await message_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args, _ = mock_update.message.reply_text.call_args
        assert expected_response in args[0]

    @patch('bot.handlers.messages.save_to_db')
    async def test_message_persistence(self, mock_save_to_db, mock_update, mock_context):
        """Test that messages are properly saved to the database"""
        from bot.handlers.messages import message_handler
        
        await message_handler(mock_update, mock_context)
        
        mock_save_to_db.assert_called_once_with(
            chat_id=mock_update.effective_chat.id,
            message=mock_update.message.text
        )

async def test_start_command(mock_update, mock_bot):
    """Test the start command handler"""
    # Arrange
    context = AsyncMock()
    context.bot = mock_bot

    # Act
    await start_command(mock_update, context)

    # Assert
    mock_bot.send_message.assert_called_once()
    args, kwargs = mock_bot.send_message.call_args
    assert "Добро пожаловать" in kwargs["text"]

async def test_help_command(mock_update, mock_bot):
    """Test the help command handler"""
    # Arrange
    context = AsyncMock()
    context.bot = mock_bot

    # Act
    await help_command(mock_update, context)

    # Assert
    mock_bot.send_message.assert_called_once()
    args, kwargs = mock_bot.send_message.call_args
    assert "Список доступных команд" in kwargs["text"]

async def test_settings_command(mock_update, mock_bot, mock_redis):
    """Test the settings command handler"""
    # Arrange
    context = AsyncMock()
    context.bot = mock_bot
    
    with patch('bot.handlers.get_redis_connection', return_value=mock_redis):
        # Act
        await settings_command(mock_update, context)
        
        # Assert
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        assert "Настройки" in kwargs["text"]

@pytest.mark.integration
async def test_user_settings_flow(mock_update, mock_bot, mock_redis):
    """Test the complete user settings flow"""
    # Arrange
    user_id = mock_update.message.from_user.id
    
    with patch('bot.utils.get_redis_connection', return_value=mock_redis):
        # Act - Get initial settings
        initial_settings = await get_user_settings(user_id)
        
        # Update settings
        new_settings = {
            "notifications": True,
            "language": "ru",
            "timezone": "Europe/Moscow"
        }
        await update_user_settings(user_id, new_settings)
        
        # Get updated settings
        updated_settings = await get_user_settings(user_id)
        
        # Assert
        assert initial_settings == {}  # Default empty settings
        assert updated_settings == new_settings

@pytest.mark.integration
async def test_error_handling(mock_update, mock_bot):
    """Test error handling in bot commands"""
    # Arrange
    context = AsyncMock()
    context.bot = mock_bot
    context.error = Exception("Test error")

    # Act
    with patch('bot.handlers.error_handler') as mock_error_handler:
        await mock_error_handler(mock_update, context)

        # Assert
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        assert "Произошла ошибка" in kwargs["text"] 