from django import forms
from .validators import InputValidator, RequestValidator, UserDataValidator, FileValidator

class ValidationMixin:
    """Миксин для добавления валидации в формы"""
    
    def clean_text_field(self, field_name: str) -> str:
        """Очистка текстового поля"""
        text = self.cleaned_data.get(field_name)
        if text:
            return InputValidator.sanitize_text(text)
        return text

    def clean_html_field(self, field_name: str) -> str:
        """Очистка HTML-поля"""
        html = self.cleaned_data.get(field_name)
        if html:
            return InputValidator.sanitize_html(html)
        return html

    def clean_email(self) -> str:
        """Очистка email"""
        email = self.cleaned_data.get('email')
        if email:
            return InputValidator.validate_email(email)
        return email

    def clean_phone(self) -> str:
        """Очистка телефона"""
        phone = self.cleaned_data.get('phone')
        if phone:
            return InputValidator.validate_phone(phone)
        return phone

    def clean_username(self) -> str:
        """Очистка имени пользователя"""
        username = self.cleaned_data.get('username')
        if username:
            return InputValidator.validate_username(username)
        return username

    def clean_password(self) -> str:
        """Очистка пароля"""
        password = self.cleaned_data.get('password')
        if password:
            return InputValidator.validate_password(password)
        return password

class RequestFormMixin(ValidationMixin):
    """Миксин для форм запросов"""
    
    def clean(self):
        cleaned_data = super().clean()
        validator = RequestValidator()
        
        try:
            cleaned_data = validator.validate_request_data(cleaned_data)
        except forms.ValidationError as e:
            self.add_error(None, e)
            
        return cleaned_data

class UserFormMixin(ValidationMixin):
    """Миксин для форм пользователя"""
    
    def clean(self):
        cleaned_data = super().clean()
        validator = UserDataValidator()
        
        try:
            cleaned_data = validator.validate_user_data(cleaned_data)
        except forms.ValidationError as e:
            self.add_error(None, e)
            
        return cleaned_data

class FileFormMixin(ValidationMixin):
    """Миксин для форм с файлами"""
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            validator = FileValidator()
            try:
                # Определяем тип файла по расширению
                ext = file.name.lower().split('.')[-1]
                if ext in validator.allowed_extensions['document']:
                    file_type = 'document'
                elif ext in validator.allowed_extensions['image']:
                    file_type = 'image'
                elif ext in validator.allowed_extensions['video']:
                    file_type = 'video'
                else:
                    raise forms.ValidationError('Неподдерживаемый тип файла')
                
                validator.validate_file(file, file_type)
            except forms.ValidationError as e:
                self.add_error('file', e)
                
        return file 