from celery import shared_task
from django.db import transaction
from .models import CRMIntegration, Request
from .services import get_crm_service, CRMRequestLog

@shared_task(bind=True, max_retries=3)
def retry_crm_sync(self, request_id: int, integration_id: int) -> None:
    """
    Повторная попытка синхронизации с CRM
    
    Args:
        request_id: ID запроса
        integration_id: ID интеграции с CRM
    """
    try:
        with transaction.atomic():
            request = Request.objects.get(id=request_id)
            integration = CRMIntegration.objects.get(id=integration_id)
            
            service = get_crm_service(integration)
            log = CRMRequestLog.objects.create(
                integration=integration,
                request=request,
                status='pending'
            )
            
            # Проверяем существующие успешные синхронизации
            existing_log = CRMRequestLog.objects.filter(
                integration=integration,
                request=request,
                status='success'
            ).first()
            
            if existing_log and existing_log.crm_entity_id:
                result = service.update_lead(existing_log.crm_entity_id, request)
            else:
                result = service.create_lead(request)
            
            # Обновляем лог
            log.crm_entity_id = result.get('id') or result.get('leadId')
            log.status = 'success'
            log.save()
            
    except Exception as e:
        log.status = 'error'
        log.error_message = f"Retry attempt {self.request.retries + 1} failed: {str(e)}"
        log.save()
        
        # Если есть еще попытки, планируем следующую
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300 * (self.request.retries + 1))  # Увеличиваем интервал с каждой попыткой 