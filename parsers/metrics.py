from prometheus_client import Counter, Histogram, start_http_server
import time

# Метрики для парсеров
PARSER_REQUESTS = Counter(
    'parser_requests_total',
    'Total number of parser requests',
    ['platform']
)

PARSER_ERRORS = Counter(
    'parser_errors_total',
    'Total number of parser errors',
    ['platform', 'error_type']
)

PARSER_REQUEST_DURATION = Histogram(
    'parser_request_duration_seconds',
    'Parser request duration in seconds',
    ['platform'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

def start_metrics_server(port=8002):
    """Запуск сервера метрик Prometheus"""
    start_http_server(port)

class MetricsMiddleware:
    """Middleware для сбора метрик парсеров"""
    
    def __init__(self, platform):
        self.platform = platform
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                PARSER_REQUESTS.labels(platform=self.platform).inc()
                return result
            except Exception as e:
                PARSER_ERRORS.labels(
                    platform=self.platform,
                    error_type=type(e).__name__
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                PARSER_REQUEST_DURATION.labels(
                    platform=self.platform
                ).observe(duration)
        return wrapper 