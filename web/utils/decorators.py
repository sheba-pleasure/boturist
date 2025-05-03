from functools import wraps
from django.http import JsonResponse
from .validators import InputValidator, RequestValidator, UserDataValidator, FileValidator

def validate_input(validator_class, fields=None):
    """
    Декоратор для валидации входных данных в представлениях
    
    :param validator_class: Класс валидатора (RequestValidator, UserDataValidator, etc.)
    :param fields: Список полей для валидации (если None, валидируются все поля)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            validator = validator_class()
            
            # Получаем данные из запроса
            data = {}
            if request.method == 'GET':
                data = request.GET.dict()
            elif request.method in ['POST', 'PUT', 'PATCH']:
                data = request.POST.dict()
                # Добавляем файлы, если есть
                if request.FILES:
                    data.update(request.FILES)
            
            # Если указаны конкретные поля, фильтруем данные
            if fields:
                data = {k: v for k, v in data.items() if k in fields}
            
            try:
                # Определяем метод валидации в зависимости от типа валидатора
                if isinstance(validator, RequestValidator):
                    clean_data = validator.validate_request_data(data)
                elif isinstance(validator, UserDataValidator):
                    clean_data = validator.validate_user_data(data)
                elif isinstance(validator, FileValidator):
                    # Для файлов проверяем каждый файл отдельно
                    clean_data = {}
                    for field_name, file in request.FILES.items():
                        if not fields or field_name in fields:
                            validator.validate_file(file, field_name)
                            clean_data[field_name] = file
                else:
                    # Для базового валидатора проверяем только текстовые поля
                    clean_data = {
                        k: InputValidator.sanitize_text(v)
                        for k, v in data.items()
                    }
                
                # Добавляем очищенные данные в request
                request.cleaned_data = clean_data
                
                return view_func(request, *args, **kwargs)
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': str(e)
                    }, status=400)
                raise
            
        return wrapper
    return decorator

def validate_json(validator_class, fields=None):
    """
    Декоратор для валидации JSON-данных в API-представлениях
    
    :param validator_class: Класс валидатора
    :param fields: Список полей для валидации
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            import json
            
            validator = validator_class()
            
            try:
                # Получаем JSON-данные
                data = json.loads(request.body)
                
                # Если указаны конкретные поля, фильтруем данные
                if fields:
                    data = {k: v for k, v in data.items() if k in fields}
                
                # Валидируем данные
                if isinstance(validator, RequestValidator):
                    clean_data = validator.validate_request_data(data)
                elif isinstance(validator, UserDataValidator):
                    clean_data = validator.validate_user_data(data)
                else:
                    clean_data = {
                        k: InputValidator.sanitize_text(v) if isinstance(v, str) else v
                        for k, v in data.items()
                    }
                
                # Добавляем очищенные данные в request
                request.cleaned_data = clean_data
                
                return view_func(request, *args, **kwargs)
                
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Неверный формат JSON'
                }, status=400)
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
            
        return wrapper
    return decorator 