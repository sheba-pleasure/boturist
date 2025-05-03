from django.shortcuts import render
import json
import hmac
import hashlib
from typing import Dict, Any
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import CRMIntegration, CRMRequestLog

def verify_webhook_signature(request, integration: CRMIntegration) -> bool:
    """Проверка подписи вебхука"""
    if not integration.webhook_secret:
        return True
        
    signature = request.headers.get('X-Webhook-Signature')
    if not signature:
        return False
        
    expected_signature = hmac.new(
        integration.webhook_secret.encode(),
        request.body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@csrf_exempt
@require_POST
def bitrix24_webhook(request):
    """Обработчик вебхуков от Bitrix24"""
    try:
        integration = CRMIntegration.objects.get(
            crm_type='bitrix24',
            is_active=True
        )
        
        if not verify_webhook_signature(request, integration):
            return HttpResponseBadRequest('Invalid signature')
            
        data = json.loads(request.body)
        
        # Обработка различных типов событий
        event_type = data.get('event')
        if event_type == 'ONCRMLEADUPDATE':
            lead_id = data['data']['FIELDS']['ID']
            # Находим и обновляем соответствующий лог
            log = CRMRequestLog.objects.filter(
                integration=integration,
                crm_entity_id=lead_id
            ).first()
            if log:
                log.external_status = data['data']['FIELDS']['STATUS_ID']
                log.save()
                
        return HttpResponse('OK')
        
    except Exception as e:
        return HttpResponseBadRequest(str(e))

@csrf_exempt
@require_POST
def amocrm_webhook(request):
    """Обработчик вебхуков от amoCRM"""
    try:
        integration = CRMIntegration.objects.get(
            crm_type='amocrm',
            is_active=True
        )
        
        if not verify_webhook_signature(request, integration):
            return HttpResponseBadRequest('Invalid signature')
            
        data = json.loads(request.body)
        
        # Обработка различных типов событий
        event_type = data.get('event')
        if event_type == 'lead_status_changed':
            lead_id = str(data['data']['id'])
            # Находим и обновляем соответствующий лог
            log = CRMRequestLog.objects.filter(
                integration=integration,
                crm_entity_id=lead_id
            ).first()
            if log:
                log.external_status = str(data['data']['status_id'])
                log.save()
                
        return HttpResponse('OK')
        
    except Exception as e:
        return HttpResponseBadRequest(str(e))

@csrf_exempt
@require_POST
def retailcrm_webhook(request):
    """Обработчик вебхуков от RetailCRM"""
    try:
        integration = CRMIntegration.objects.get(
            crm_type='retailcrm',
            is_active=True
        )
        
        if not verify_webhook_signature(request, integration):
            return HttpResponseBadRequest('Invalid signature')
            
        data = json.loads(request.body)
        
        # Обработка различных типов событий
        event_type = data.get('type')
        if event_type == 'lead.status.changed':
            lead_id = data['data']['id']
            # Находим и обновляем соответствующий лог
            log = CRMRequestLog.objects.filter(
                integration=integration,
                crm_entity_id=lead_id
            ).first()
            if log:
                log.external_status = data['data']['status']
                log.save()
                
        return HttpResponse('OK')
        
    except Exception as e:
        return HttpResponseBadRequest(str(e))
