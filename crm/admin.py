from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import CRMIntegration, CRMFieldMapping, CRMRequestLog

class CRMFieldMappingInline(admin.TabularInline):
    model = CRMFieldMapping
    extra = 1
    fields = ('local_field', 'crm_field', 'field_type', 'is_required', 'default_value')

@admin.register(CRMIntegration)
class CRMIntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'crm_type', 'is_active', 'api_endpoint', 'created_at', 'updated_at')
    list_filter = ('crm_type', 'is_active', 'created_at')
    search_fields = ('name', 'api_endpoint')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CRMFieldMappingInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'crm_type', 'is_active')
        }),
        ('API настройки', {
            'fields': ('api_endpoint', 'api_key', 'webhook_url')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(CRMFieldMapping)
class CRMFieldMappingAdmin(admin.ModelAdmin):
    list_display = ('integration', 'local_field', 'crm_field', 'field_type', 'is_required')
    list_filter = ('integration', 'field_type', 'is_required')
    search_fields = ('local_field', 'crm_field')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('integration')

@admin.register(CRMRequestLog)
class CRMRequestLogAdmin(admin.ModelAdmin):
    list_display = ('request_link', 'integration_link', 'status', 'crm_entity_id', 'created_at')
    list_filter = ('status', 'integration', 'created_at')
    search_fields = ('request__query', 'crm_entity_id', 'error_message')
    readonly_fields = ('created_at', 'updated_at')
    
    def request_link(self, obj):
        url = reverse('admin:admin_panel_request_change', args=[obj.request.id])
        return format_html('<a href="{}">{}</a>', url, obj.request)
    request_link.short_description = 'Запрос'
    
    def integration_link(self, obj):
        url = reverse('admin:crm_crmintegration_change', args=[obj.integration.id])
        return format_html('<a href="{}">{}</a>', url, obj.integration)
    integration_link.short_description = 'CRM интеграция'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('request', 'integration') 