from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django_prometheus.models import ExportModelOperationsMixin

from .models import Request, RequestFile, RequestMessage

@receiver(post_save, sender=Request)
def request_saved(sender, instance, created, **kwargs):
    """Обработчик сохранения заявки"""
    # Инвалидируем кеш
    cache.delete(f'request_{instance.id}')
    cache.delete('requests_count')
    
    if created:
        # Создаем системное сообщение о создании заявки
        RequestMessage.objects.create(
            request=instance,
            sender_type='system',
            message='Заявка создана'
        )

@receiver(post_save, sender=RequestMessage)
def message_saved(sender, instance, created, **kwargs):
    """Обработчик сохранения сообщения"""
    if created:
        # Обновляем время последнего обновления заявки
        instance.request.save(update_fields=['updated_at'])
        
        # Инвалидируем кеш
        cache.delete(f'request_messages_{instance.request_id}')

@receiver(post_delete, sender=RequestFile)
def file_deleted(sender, instance, **kwargs):
    """Обработчик удаления файла"""
    # Инвалидируем кеш
    cache.delete(f'request_files_{instance.request_id}') 