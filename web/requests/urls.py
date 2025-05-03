from django.urls import path
from . import views

app_name = 'requests'

urlpatterns = [
    path('files/<int:file_id>/download/', views.request_file_download, name='request-file-download'),
    path('files/<int:file_id>/preview/', views.request_file_preview, name='request-file-preview'),
] 