import pytest
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.db.utils import OperationalError

@pytest.mark.django_db
class TestHealthCheck:
    def test_health_check_success(self, client, mock_redis):
        """Test health check when all services are healthy"""
        with patch('web.dashboard.views.Redis.from_url', return_value=mock_redis):
            response = client.get(reverse('health_check'))
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['database'] is True
            assert data['redis'] is True

    def test_health_check_db_failure(self, client, mock_redis):
        """Test health check when database is down"""
        with patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection',
                  side_effect=OperationalError("Database error")):
            with patch('web.dashboard.views.Redis.from_url', return_value=mock_redis):
                response = client.get(reverse('health_check'))
                assert response.status_code == 503
                data = response.json()
                assert data['status'] == 'unhealthy'
                assert data['database'] is False
                assert 'Database error' in data['details']['database']

    def test_health_check_redis_failure(self, client):
        """Test health check when Redis is down"""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Redis connection error")
        
        with patch('web.dashboard.views.Redis.from_url', return_value=mock_redis):
            response = client.get(reverse('health_check'))
            assert response.status_code == 503
            data = response.json()
            assert data['status'] == 'unhealthy'
            assert data['redis'] is False
            assert 'Redis connection error' in data['details']['redis'] 