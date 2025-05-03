from django.urls import path
from . import views

app_name = 'crm_integration'

urlpatterns = [
    path('webhooks/bitrix24/', views.bitrix24_webhook, name='bitrix24_webhook'),
    path('webhooks/amocrm/', views.amocrm_webhook, name='amocrm_webhook'),
    path('webhooks/retailcrm/', views.retailcrm_webhook, name='retailcrm_webhook'),
] 