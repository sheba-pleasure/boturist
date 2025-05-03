from django.db.models.signals import post_save
from django.dispatch import receiver
from admin_panel.models import Request
from .services import sync_request_with_crm

@receiver(post_save, sender=Request)
def request_saved(sender, instance, created, **kwargs):
    """Обработчик сохранения запроса"""
    # Синхронизируем с CRM только если статус изменился или это новый запрос
    if created or instance.tracker.has_changed('status'):
        sync_request_with_crm(instance) 