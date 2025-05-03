from django.db import models
from django.utils.translation import gettext_lazy as _
from admin_panel.models import Request, TelegramUser

class CRMIntegration(models.Model):
    """Модель для хранения настроек интеграции с CRM"""
    
    CRM_TYPE_CHOICES = [
        ('bitrix24', 'Bitrix24'),
        ('amocrm', 'amoCRM'),
        ('retailcrm', 'RetailCRM'),
    ]

    name = models.CharField(_('Название'), max_length=100)
    crm_type = models.CharField(_('Тип CRM'), max_length=20, choices=CRM_TYPE_CHOICES)
    api_endpoint = models.URLField(_('API endpoint'))
    api_key = models.CharField(_('API ключ'), max_length=255)
    webhook_url = models.URLField(_('Webhook URL'), blank=True, null=True)
    webhook_secret = models.CharField(_('Webhook Secret'), max_length=255, blank=True, help_text=_('Секретный ключ для проверки подписи вебхуков'))
    is_active = models.BooleanField(_('Активно'), default=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)

    class Meta:
        verbose_name = 'CRM интеграция'
        verbose_name_plural = 'CRM интеграции'

    def __str__(self):
        return f"{self.name} ({self.get_crm_type_display()})"

class CRMFieldMapping(models.Model):
    """Модель для маппинга полей между системами"""
    
    FIELD_TYPES = [
        ('text', 'Текстовое поле'),
        ('number', 'Числовое поле'),
        ('date', 'Дата'),
        ('enum', 'Список'),
        ('bool', 'Логическое'),
    ]

    integration = models.ForeignKey(
        CRMIntegration,
        on_delete=models.CASCADE,
        related_name='field_mappings'
    )
    local_field = models.CharField(_('Локальное поле'), max_length=100)
    crm_field = models.CharField(_('Поле в CRM'), max_length=100)
    field_type = models.CharField(_('Тип поля'), max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(_('Обязательное'), default=False)
    default_value = models.CharField(_('Значение по умолчанию'), max_length=255, blank=True)

    class Meta:
        verbose_name = 'Маппинг полей CRM'
        verbose_name_plural = 'Маппинги полей CRM'
        unique_together = ['integration', 'local_field', 'crm_field']

    def __str__(self):
        return f"{self.local_field} -> {self.crm_field}"

class CRMRequestLog(models.Model):
    """Модель для логирования синхронизации с CRM"""
    
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
        ('pending', 'В обработке'),
    ]

    integration = models.ForeignKey(CRMIntegration, on_delete=models.CASCADE)
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    crm_entity_id = models.CharField(_('ID в CRM'), max_length=100, blank=True)
    status = models.CharField(_('Статус'), max_length=20, choices=STATUS_CHOICES)
    external_status = models.CharField(_('Статус в CRM'), max_length=100, blank=True, help_text=_('Статус сущности в CRM системе'))
    error_message = models.TextField(_('Сообщение об ошибке'), blank=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)

    class Meta:
        verbose_name = 'Лог синхронизации с CRM'
        verbose_name_plural = 'Логи синхронизации с CRM'
        ordering = ['-created_at']

    def __str__(self):
        return f"Синхронизация заявки #{self.request_id} ({self.get_status_display()})"
