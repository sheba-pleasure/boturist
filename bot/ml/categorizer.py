from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import joblib
import os
from datetime import datetime
import logging
from celery import shared_task
from web.utils.form_mixins import RequestFormMixin, UserFormMixin, FileFormMixin
from django import forms
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from pymongo import MongoClient
from web.utils.decorators import validate_input, validate_json
from web.utils.validators import RequestValidator, UserDataValidator, InputValidator, FileValidator

logger = logging.getLogger(__name__)

# Определение моделей
class Request(models.Model):
    text = models.TextField()
    category = models.CharField(max_length=50)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'bot'

class Document(models.Model):
    file = models.FileField(upload_to='documents/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'bot'

class MessageCategorizer:
    CATEGORIES = {
        'consultation': 'Консультация',
        'complaint': 'Жалоба',
        'pricing': 'Вопрос по ценам',
        'documentation': 'Документы',
        'other': 'Прочее'
    }

    def __init__(self):
        self.model_path = 'bot/ml/models/categorizer.joblib'
        self.pipeline = self._load_or_create_model()

    def _load_or_create_model(self) -> Pipeline:
        """Load existing model or create new one"""
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        
        return Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('clf', MultinomialNB())
        ])

    def train(self, texts: List[str], labels: List[str]) -> None:
        """Train the model on new data"""
        try:
            self.pipeline.fit(texts, labels)
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.pipeline, self.model_path)
            logger.info("Model trained and saved successfully")
        except Exception as e:
            logger.error(f"Error training model: {e}")

    def predict(self, text: str) -> Tuple[str, float]:
        """Predict category for a message"""
        try:
            # Get prediction and probability
            category = self.pipeline.predict([text])[0]
            proba = np.max(self.pipeline.predict_proba([text]))
            return category, float(proba)
        except Exception as e:
            logger.error(f"Error predicting category: {e}")
            return 'other', 0.0

    def save_to_mongodb(self, text: str, predicted_category: str, 
                       probability: float, actual_category: str = None) -> None:
        """Save categorization result to MongoDB for future training"""
        client = MongoClient(settings.MONGODB_URI)
        db = client.bot_data

        db.categorization.insert_one({
            'text': text,
            'predicted_category': predicted_category,
            'probability': probability,
            'actual_category': actual_category,
            'created_at': datetime.utcnow()
        })

@shared_task
def categorize_message(text: str) -> Dict:
    """Celery task to categorize message"""
    categorizer = MessageCategorizer()
    category, probability = categorizer.predict(text)
    
    # Save result for future training
    categorizer.save_to_mongodb(text, category, probability)
    
    return {
        'category': category,
        'category_name': MessageCategorizer.CATEGORIES.get(category, 'Прочее'),
        'probability': probability
    }

@shared_task
def train_categorizer(min_probability: float = 0.8) -> None:
    """Retrain model on high-confidence predictions"""
    client = MongoClient(settings.MONGODB_URI)
    db = client.bot_data

    # Get high-confidence predictions
    data = db.categorization.find({
        'probability': {'$gte': min_probability},
        'actual_category': {'$exists': True}  # Only use verified categories
    })

    texts = []
    labels = []
    for item in data:
        texts.append(item['text'])
        labels.append(item['actual_category'])

    if texts and labels:
        categorizer = MessageCategorizer()
        categorizer.train(texts, labels)
        logger.info(f"Model retrained on {len(texts)} examples")

class UserRegistrationForm(UserFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']

class RequestForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = Request
        fields = ['text', 'category', 'email']

class DocumentUploadForm(FileFormMixin, forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file', 'description']

@validate_input(RequestValidator)
def handle_request(request):
    # Данные уже проверены и доступны в request.cleaned_data
    data = request.cleaned_data
    # Обработка данных
    return data

@validate_json(UserDataValidator, fields=['username', 'email'])
def api_update_user(request):
    # JSON-данные проверены и доступны в request.cleaned_data
    data = request.cleaned_data
    # Обработка данных
    return data

# Пример использования валидаторов
def example_validation(request):
    # Проверка текста
    sample_text = "Пример текста для проверки"
    clean_text = InputValidator.sanitize_text(sample_text)

    # Проверка файла
    file_validator = FileValidator()
    if file_validator.validate_file(request.FILES.get('document'), 'document'):
        # Файл прошел проверку
        return True
    return False

@validate_input(RequestValidator)
def some_view(request):
    validation_result = example_validation(request)
    # Дальнейшая обработка... 