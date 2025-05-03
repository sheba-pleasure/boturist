from django.apps import AppConfig


class CrmNewConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm_new'
    verbose_name = 'CRM интеграция'

    def ready(self):
        import crm_new.signals  # noqa
