import pytest
from django.conf import settings
from redis import Redis
from django.test import Client
import mongomock
import fakeredis
import os
import django
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User, Chat, Message, Bot

# Setup Django settings for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.web.settings')
django.setup()

@pytest.fixture
def client():
    """Django test client fixture"""
    return Client()

@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing"""
    return fakeredis.FakeStrictRedis()

@pytest.fixture
def mock_mongodb():
    """Mock MongoDB connection for testing"""
    return mongomock.MongoClient()

@pytest.fixture
def test_settings(settings):
    """Test settings with test database configurations"""
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'
        }
    }
    settings.REDIS_URL = 'redis://localhost:6379/0'
    return settings

@pytest.fixture
async def mock_bot():
    """Mock Telegram Bot instance"""
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.delete_message = AsyncMock()
    return bot

@pytest.fixture
def mock_user():
    """Mock Telegram User instance"""
    return User(
        id=123456789,
        first_name="Test",
        is_bot=False,
        username="testuser"
    )

@pytest.fixture
def mock_chat():
    """Mock Telegram Chat instance"""
    return Chat(
        id=123456789,
        type="private"
    )

@pytest.fixture
def mock_message():
    """Mock Telegram Message instance"""
    return Message(
        message_id=1,
        date=None,
        chat=None
    )

@pytest.fixture
async def mock_update(mock_message, mock_chat, mock_user):
    """Mock Telegram Update instance"""
    mock_message.chat = mock_chat
    mock_message.from_user = mock_user
    update = Update(update_id=1)
    update.message = mock_message
    return update

@pytest.fixture
def celery_app(settings):
    """Configure Celery for testing"""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    return settings 