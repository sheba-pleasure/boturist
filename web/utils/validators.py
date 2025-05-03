import re
from typing import Any, Dict, Optional, Union
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
import bleach

class InputValidator:
    """Базовый класс для валидации входных данных"""
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Санитизация текстового ввода"""
        # Удаляем HTML-теги
        text = strip_tags(text)
        # Нормализуем пробелы
        text = ' '.join(text.split())
        return text.strip()

    @staticmethod
    def sanitize_html(html: str) -> str:
        """Санитизация HTML с сохранением разрешенных тегов"""
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ul', 'li', 'ol']
        allowed_attrs = {'*': ['class']}
        return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

    @staticmethod
    def validate_phone(phone: str) -> str:
        """Валидация телефонного номера"""
        phone = re.sub(r'\D', '', phone)
        if not re.match(r'^\d{11}$', phone):
            raise ValidationError('Неверный формат телефонного номера')
        return phone

    @staticmethod
    def validate_email(email: str) -> str:
        """Валидация email"""
        email = email.lower().strip()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError('Неверный формат email')
        return email

    @staticmethod
    def validate_username(username: str) -> str:
        """Валидация имени пользователя"""
        username = username.strip()
        if not re.match(r'^[\w\d_]{3,30}$', username):
            raise ValidationError('Имя пользователя должно содержать от 3 до 30 символов (буквы, цифры и _)')
        return username

    @staticmethod
    def validate_password(password: str) -> str:
        """Валидация пароля"""
        if len(password) < 8:
            raise ValidationError('Пароль должен содержать минимум 8 символов')
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', password):
            raise ValidationError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'\d', password):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру')
        return password

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
        """Валидация расширения файла"""
        ext = filename.lower().split('.')[-1]
        if ext not in allowed_extensions:
            raise ValidationError(f'Недопустимое расширение файла. Разрешены: {", ".join(allowed_extensions)}')
        return True

    @staticmethod
    def validate_file_size(file_size: int, max_size: int) -> bool:
        """Валидация размера файла"""
        if file_size > max_size:
            raise ValidationError(f'Размер файла превышает максимально допустимый ({max_size} байт)')
        return True

class RequestValidator(InputValidator):
    """Валидатор для запросов от пользователей"""
    
    def validate_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных запроса"""
        clean_data = {}
        
        # Базовая валидация текстовых полей
        if 'text' in data:
            clean_data['text'] = self.sanitize_text(data['text'])
            
        if 'description' in data:
            clean_data['description'] = self.sanitize_text(data['description'])
            
        if 'email' in data:
            clean_data['email'] = self.validate_email(data['email'])
            
        if 'phone' in data:
            clean_data['phone'] = self.validate_phone(data['phone'])
            
        # Валидация категории
        if 'category' in data:
            clean_data['category'] = self.validate_category(data['category'])
            
        return clean_data

    @staticmethod
    def validate_category(category: str) -> str:
        """Валидация категории запроса"""
        allowed_categories = ['consultation', 'complaint', 'pricing', 'documentation', 'other']
        if category not in allowed_categories:
            raise ValidationError('Недопустимая категория')
        return category

class UserDataValidator(InputValidator):
    """Валидатор для пользовательских данных"""
    
    def validate_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных пользователя"""
        clean_data = {}
        
        if 'username' in data:
            clean_data['username'] = self.validate_username(data['username'])
            
        if 'email' in data:
            clean_data['email'] = self.validate_email(data['email'])
            
        if 'password' in data:
            clean_data['password'] = self.validate_password(data['password'])
            
        if 'phone' in data:
            clean_data['phone'] = self.validate_phone(data['phone'])
            
        return clean_data

class FileValidator(InputValidator):
    """Валидатор для файлов"""
    
    def __init__(self):
        self.allowed_extensions = {
            'document': ['pdf', 'doc', 'docx', 'txt', 'rtf'],
            'image': ['jpg', 'jpeg', 'png', 'gif'],
            'video': ['mp4', 'avi', 'mov']
        }
        self.max_sizes = {
            'document': 10 * 1024 * 1024,  # 10MB
            'image': 5 * 1024 * 1024,      # 5MB
            'video': 50 * 1024 * 1024      # 50MB
        }

    def validate_file(self, file: Any, file_type: str) -> bool:
        """Валидация файла"""
        if file_type not in self.allowed_extensions:
            raise ValidationError('Недопустимый тип файла')
            
        # Проверка расширения
        self.validate_file_extension(
            file.name, 
            self.allowed_extensions[file_type]
        )
        
        # Проверка размера
        self.validate_file_size(
            file.size, 
            self.max_sizes[file_type]
        )
        
        return True 