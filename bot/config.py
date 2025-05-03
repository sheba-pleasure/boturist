from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the bot"""
    
    # Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
    
    # Database Configuration
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "db"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "boturist"),
        "user": os.getenv("DB_USER", "boturist"),
        "password": os.getenv("DB_PASSWORD"),
    }
    
    # Redis Configuration
    REDIS_CONFIG = {
        "host": os.getenv("REDIS_HOST", "redis"),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": 0,
    }
    
    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/boturist")
    
    # External APIs Configuration
    VK_API_TOKEN = os.getenv("VK_API_TOKEN")
    INSTAGRAM_API_TOKEN = os.getenv("INSTAGRAM_API_TOKEN")
    YANDEX_MAPS_API_KEY = os.getenv("YANDEX_MAPS_API_KEY")
    GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")
    
    # S3 Storage Configuration
    AWS_CONFIG = {
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
    }
    
    # Sentry Configuration
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Bot Settings
    ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
    MAX_MESSAGE_LENGTH = 4096
    RATE_LIMIT = 30  # messages per minute
    
    # File Settings
    FILE_SETTINGS = {
        # Максимальные размеры файлов (в байтах)
        "max_file_size": 50 * 1024 * 1024,  # 50MB общий лимит
        "max_photo_size": 10 * 1024 * 1024,  # 10MB для фото
        "max_video_size": 20 * 1024 * 1024,  # 20MB для видео
        
        # Разрешенные типы файлов
        "allowed_mime_types": {
            "document": [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "text/plain",
                "application/zip",
                "application/x-rar-compressed"
            ],
            "image": [
                "image/jpeg",
                "image/png",
                "image/gif"
            ],
            "video": [
                "video/mp4",
                "video/quicktime",
                "video/x-msvideo"
            ]
        },
        
        # Настройки предпросмотра
        "preview_image_size": 800,  # максимальная сторона изображения для предпросмотра
        "preview_quality": 85,      # качество JPEG для предпросмотра
    }
    
    # Feature Flags
    ENABLE_NLP = os.getenv("ENABLE_NLP", "true").lower() == "true"
    ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ENABLE_AUTO_REPLY = os.getenv("ENABLE_AUTO_REPLY", "true").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            "TELEGRAM_BOT_TOKEN",
            "DB_CONFIG",
            "REDIS_CONFIG",
            "MONGO_URI",
        ]
        
        for var in required_vars:
            if not getattr(cls, var):
                raise ValueError(f"Missing required configuration: {var}")
        
        return True
    
    @classmethod
    def get_db_url(cls) -> str:
        """Get database URL"""
        return (
            f"postgresql://{cls.DB_CONFIG['user']}:{cls.DB_CONFIG['password']}"
            f"@{cls.DB_CONFIG['host']}:{cls.DB_CONFIG['port']}/{cls.DB_CONFIG['database']}"
        )
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis URL"""
        return f"redis://{cls.REDIS_CONFIG['host']}:{cls.REDIS_CONFIG['port']}/{cls.REDIS_CONFIG['db']}" 