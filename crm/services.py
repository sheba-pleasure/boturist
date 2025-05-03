import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from django.conf import settings
from .models import CRMIntegration, CRMRequestLog, Request

class BaseCRMService(ABC):
    """Базовый класс для работы с CRM системами"""
    
    def __init__(self, integration: CRMIntegration):
        self.integration = integration
        self.api_endpoint = integration.api_endpoint
        self.api_key = integration.api_key

    @abstractmethod
    def create_lead(self, request: Request) -> Dict[str, Any]:
        """Создание лида в CRM"""
        pass

    @abstractmethod
    def update_lead(self, crm_entity_id: str, request: Request) -> Dict[str, Any]:
        """Обновление лида в CRM"""
        pass

    def map_fields(self, request: Request) -> Dict[str, Any]:
        """Маппинг полей из запроса в поля CRM"""
        mapped_data = {}
        for mapping in self.integration.field_mappings.all():
            value = self.get_field_value(request, mapping.local_field)
            if value is None and mapping.default_value:
                value = mapping.default_value
            if mapping.is_required and value is None:
                raise ValueError(f"Required field {mapping.local_field} is missing")
            mapped_data[mapping.crm_field] = value
        return mapped_data

    def get_field_value(self, request: Request, field_name: str) -> Optional[Any]:
        """Получение значения поля из запроса"""
        if field_name == 'telegram_id':
            return request.user.telegram_id
        elif field_name == 'username':
            return request.user.username
        elif field_name == 'platform':
            return request.platform
        elif field_name == 'query':
            return request.query
        elif field_name == 'status':
            return request.status
        return None

class Bitrix24Service(BaseCRMService):
    """Сервис для работы с Bitrix24"""

    def create_lead(self, request: Request) -> Dict[str, Any]:
        mapped_data = self.map_fields(request)
        response = requests.post(
            f"{self.api_endpoint}/crm.lead.add",
            json={
                'fields': mapped_data,
                'auth': self.api_key
            }
        )
        response.raise_for_status()
        return response.json()

    def update_lead(self, crm_entity_id: str, request: Request) -> Dict[str, Any]:
        mapped_data = self.map_fields(request)
        response = requests.post(
            f"{self.api_endpoint}/crm.lead.update",
            json={
                'id': crm_entity_id,
                'fields': mapped_data,
                'auth': self.api_key
            }
        )
        response.raise_for_status()
        return response.json()

class AmoCRMService(BaseCRMService):
    """Сервис для работы с amoCRM"""

    def create_lead(self, request: Request) -> Dict[str, Any]:
        mapped_data = self.map_fields(request)
        response = requests.post(
            f"{self.api_endpoint}/api/v4/leads",
            headers={'Authorization': f'Bearer {self.api_key}'},
            json=[mapped_data]
        )
        response.raise_for_status()
        return response.json()

    def update_lead(self, crm_entity_id: str, request: Request) -> Dict[str, Any]:
        mapped_data = self.map_fields(request)
        response = requests.patch(
            f"{self.api_endpoint}/api/v4/leads/{crm_entity_id}",
            headers={'Authorization': f'Bearer {self.api_key}'},
            json=mapped_data
        )
        response.raise_for_status()
        return response.json()

class RetailCRMService(BaseCRMService):
    """Сервис для работы с RetailCRM"""

    def create_lead(self, request: Request) -> Dict[str, Any]:
        mapped_data = self.map_fields(request)
        response = requests.post(
            f"{self.api_endpoint}/api/v5/leads/create",
            headers={'X-API-KEY': self.api_key},
            json={'lead': mapped_data}
        )
        response.raise_for_status()
        return response.json()

    def update_lead(self, crm_entity_id: str, request: Request) -> Dict[str, Any]:
        mapped_data = self.map_fields(request)
        response = requests.post(
            f"{self.api_endpoint}/api/v5/leads/{crm_entity_id}/edit",
            headers={'X-API-KEY': self.api_key},
            json={'lead': mapped_data}
        )
        response.raise_for_status()
        return response.json()

def get_crm_service(integration: CRMIntegration) -> BaseCRMService:
    """Фабричный метод для получения сервиса CRM"""
    services = {
        'bitrix24': Bitrix24Service,
        'amocrm': AmoCRMService,
        'retailcrm': RetailCRMService
    }
    service_class = services.get(integration.crm_type)
    if not service_class:
        raise ValueError(f"Unsupported CRM type: {integration.crm_type}")
    return service_class(integration)

def sync_request_with_crm(request: Request) -> None:
    """Синхронизация запроса с CRM системами"""
    for integration in CRMIntegration.objects.filter(is_active=True):
        try:
            service = get_crm_service(integration)
            log = CRMRequestLog.objects.create(
                integration=integration,
                request=request,
                status='pending'
            )
            
            # Создаем или обновляем лид в CRM
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
            log.error_message = str(e)
            log.save() 