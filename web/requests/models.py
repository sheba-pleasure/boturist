from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TelegramUser(models.Model):
    """Модель для хранения пользователей Telegram"""
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Telegram пользователь'
        verbose_name_plural = 'Telegram пользователи'
        
    def __str__(self):
        return f"{self.username or self.telegram_id}"

class Request(models.Model):
    """Модель для хранения заявок"""
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В обработке'),
        ('waiting', 'Ожидает ответа'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    
    CATEGORY_CHOICES = [
        ('general', 'Общий вопрос'),
        ('technical', 'Техническая поддержка'),
        ('billing', 'Оплата и счета'),
        ('other', 'Другое'),
    ]
    
    telegram_user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='requests')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')
    
    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Заявка #{self.id} от {self.telegram_user}"

class RequestFile(models.Model):
    """Модель для хранения файлов, прикрепленных к заявкам"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='files')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    file_size = models.BigIntegerField()  # размер в байтах
    s3_key = models.CharField(max_length=500)  # путь к файлу в S3
    preview_key = models.CharField(max_length=500, null=True, blank=True)  # путь к превью в S3
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Файл заявки'
        verbose_name_plural = 'Файлы заявок'
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"Файл {self.file_name} (Заявка #{self.request_id})"

class RequestMessage(models.Model):
    """Модель для хранения сообщений в заявке"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=20, choices=[
        ('user', 'Пользователь'),
        ('admin', 'Администратор'),
        ('system', 'Система'),
    ])
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    telegram_user = models.ForeignKey(TelegramUser, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Сообщение заявки'
        verbose_name_plural = 'Сообщения заявок'
        ordering = ['created_at']
        
    def __str__(self):
        return f"Сообщение в заявке #{self.request_id} от {self.sender_type}"
