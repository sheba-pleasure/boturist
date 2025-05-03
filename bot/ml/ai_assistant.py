from abc import ABC, abstractmethod
from typing import Optional, Dict
import logging
from datetime import datetime
import asyncio
from enum import Enum
import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class ModelType(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    LOCAL = "local"

class AIModelError(Exception):
    """Base exception for AI model errors"""
    pass

class TokenLimitError(AIModelError):
    """Raised when input exceeds token limit"""
    pass

class APIError(AIModelError):
    """Raised when API call fails"""
    pass

class BaseAIModel(ABC):
    """Abstract base class for AI models"""
    
    def __init__(self):
        self.max_input_length = 4096  # Default max tokens
        self.timeout = 30  # Default timeout in seconds

    @abstractmethod
    async def generate_response(self, message: str) -> str:
        """Generate response from AI model"""
        pass

    def validate_input(self, message: str) -> None:
        """Validate input message length"""
        if len(message) > self.max_input_length:
            raise TokenLimitError(f"Input length {len(message)} exceeds limit {self.max_input_length}")

class OpenAIModel(BaseAIModel):
    def __init__(self):
        super().__init__()
        self.api_key = settings.OPENAI_API_KEY
        self.model = "gpt-3.5-turbo"
        self.max_input_length = 4000

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, message: str) -> str:
        self.validate_input(message)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": message}],
                        "max_tokens": 1000
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                raise AIModelError("Request timed out")
            except Exception as e:
                raise APIError(f"OpenAI API error: {str(e)}")

class GeminiModel(BaseAIModel):
    def __init__(self):
        super().__init__()
        self.api_key = settings.GEMINI_API_KEY
        self.max_input_length = 30000

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, message: str) -> str:
        self.validate_input(message)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": message}]}]
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except httpx.TimeoutException:
                raise AIModelError("Request timed out")
            except Exception as e:
                raise APIError(f"Gemini API error: {str(e)}")

class OllamaModel(BaseAIModel):
    def __init__(self):
        super().__init__()
        self.api_url = settings.OLLAMA_API_URL
        self.model = "llama2"
        self.max_input_length = 4096

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, message: str) -> str:
        self.validate_input(message)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": message
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()["response"]
            except httpx.TimeoutException:
                raise AIModelError("Request timed out")
            except Exception as e:
                raise APIError(f"Ollama API error: {str(e)}")

class AIAssistant:
    """Main class for handling AI assistant functionality"""
    
    def __init__(self, model_type: ModelType = ModelType.OPENAI):
        self.model_type = model_type
        self.model = self._get_model_instance()
        
    def _get_model_instance(self) -> BaseAIModel:
        """Get instance of specified AI model"""
        models = {
            ModelType.OPENAI: OpenAIModel,
            ModelType.GEMINI: GeminiModel,
            ModelType.OLLAMA: OllamaModel
        }
        
        if self.model_type not in models:
            raise ValueError(f"Unsupported model type: {self.model_type}")
            
        return models[self.model_type]()

    async def get_response(self, message: str) -> str:
        """Get response from AI model with error handling"""
        try:
            return await self.model.generate_response(message)
        except TokenLimitError as e:
            return "Извините, ваше сообщение слишком длинное. Пожалуйста, сократите его."
        except AIModelError as e:
            logger.error(f"AI model error: {str(e)}")
            return "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже."
        except Exception as e:
            logger.error(f"Unexpected error in AI assistant: {str(e)}")
            return "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."

    async def log_interaction(self, user_id: int, message: str, response: str) -> None:
        """Log interaction with AI model to MongoDB"""
        from pymongo import MongoClient
        
        client = MongoClient(settings.MONGODB_URI)
        db = client.bot_data
        
        db.ai_interactions.insert_one({
            'user_id': user_id,
            'model_type': self.model_type.value,
            'message': message,
            'response': response,
            'timestamp': datetime.utcnow()
        }) 