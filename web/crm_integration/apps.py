from django.apps import AppConfig


class CrmIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm_integration'
    verbose_name = 'CRM интеграция'

    def ready(self):
        import crm_integration.signals  # noqa
