from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

from bot.content import RequestFileManager
from bot.database import Database

class RequestFileManagerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Инициализируем менеджер файлов только если включена работа с файлами
        if not getattr(settings, 'ENABLE_FILE_UPLOADS', True):
            raise MiddlewareNotUsed('File uploads are disabled')
            
        self.db = Database()
        self.file_manager = RequestFileManager(self.db)
    
    def __call__(self, request):
        # Добавляем менеджер файлов в объект запроса
        request.file_manager = self.file_manager
        return self.get_response(request) 