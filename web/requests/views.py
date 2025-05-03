from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from .models import RequestFile

# Create your views here.

@login_required
@require_http_methods(["GET"])
def request_file_download(request, file_id):
    """Скачивание файла"""
    file = get_object_or_404(RequestFile, id=file_id)
    
    # Получаем URL для скачивания
    file_manager = request.file_manager  # Инициализируется в middleware
    file_url = file_manager.get_file_url(file_id)
    
    if not file_url:
        raise Http404("Файл не найден")
    
    # Перенаправляем на URL для скачивания
    response = HttpResponse()
    response['X-Accel-Redirect'] = file_url['file_url']
    response['Content-Type'] = file.file_type
    response['Content-Disposition'] = f'attachment; filename="{file.file_name}"'
    return response

@login_required
@require_http_methods(["GET"])
def request_file_preview(request, file_id):
    """Получение превью файла"""
    file = get_object_or_404(RequestFile, id=file_id)
    
    if not file.preview_key:
        raise Http404("Превью не найдено")
    
    # Получаем URL превью
    file_manager = request.file_manager
    file_url = file_manager.get_file_url(file_id, preview=True)
    
    if not file_url or 'preview_url' not in file_url:
        raise Http404("Превью не найдено")
    
    # Перенаправляем на URL превью
    response = HttpResponse()
    response['X-Accel-Redirect'] = file_url['preview_url']
    response['Content-Type'] = 'image/jpeg'
    return response
