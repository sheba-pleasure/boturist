from django.apps import AppConfig


class RequestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'requests'
    verbose_name = 'Заявки'

    def ready(self):
        """Импортируем сигналы при загрузке приложения"""
        import requests.signals  # noqa
