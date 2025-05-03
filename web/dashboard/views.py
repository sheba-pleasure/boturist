from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError
from redis import Redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Create your views here.

def health_check(request):
    """
    Health check endpoint that verifies database and redis connections
    """
    health_status = {
        'status': 'healthy',
        'database': True,
        'redis': True,
        'details': {}
    }
    
    # Check database connection
    try:
        connections['default'].ensure_connection()
    except OperationalError as e:
        health_status['database'] = False
        health_status['status'] = 'unhealthy'
        health_status['details']['database'] = str(e)
        logger.error(f"Database health check failed: {e}")

    # Check Redis connection
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
    except Exception as e:
        health_status['redis'] = False
        health_status['status'] = 'unhealthy'
        health_status['details']['redis'] = str(e)
        logger.error(f"Redis health check failed: {e}")

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
