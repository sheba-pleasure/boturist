import pytest
from unittest.mock import Mock, patch
from config.api_keys import APIKeyManager
import json
from datetime import datetime, timedelta

@pytest.fixture
def mock_redis():
    with patch('redis.Redis') as mock:
        yield mock.from_url.return_value

@pytest.fixture
def api_key_manager(mock_redis):
    return APIKeyManager()

def test_set_key(api_key_manager, mock_redis):
    # Arrange
    service = "test_service"
    key = "test_key"
    
    # Act
    result = api_key_manager.set_key(service, key)
    
    # Assert
    assert result is True
    mock_redis.set.assert_called_once()
    args = mock_redis.set.call_args[0]
    assert args[0] == "api_keys:test_service"
    data = json.loads(args[1])
    assert data['key'] == key
    assert 'created_at' in data

def test_set_key_with_expiration(api_key_manager, mock_redis):
    # Arrange
    service = "test_service"
    key = "test_key"
    expires_in_days = 30
    
    # Act
    result = api_key_manager.set_key(service, key, expires_in_days)
    
    # Assert
    assert result is True
    mock_redis.expire.assert_called_once()
    args = mock_redis.expire.call_args[0]
    assert args[0] == "api_keys:test_service"
    assert isinstance(args[1], timedelta)
    assert args[1].days == expires_in_days

def test_get_key(api_key_manager, mock_redis):
    # Arrange
    service = "test_service"
    key = "test_key"
    mock_redis.get.return_value = json.dumps({
        'key': key,
        'created_at': datetime.utcnow().isoformat(),
        'last_used': None
    })
    
    # Act
    result = api_key_manager.get_key(service)
    
    # Assert
    assert result == key
    mock_redis.get.assert_called_once_with("api_keys:test_service")

def test_get_nonexistent_key(api_key_manager, mock_redis):
    # Arrange
    mock_redis.get.return_value = None
    
    # Act
    result = api_key_manager.get_key("nonexistent")
    
    # Assert
    assert result is None

def test_delete_key(api_key_manager, mock_redis):
    # Arrange
    service = "test_service"
    mock_redis.delete.return_value = 1
    
    # Act
    result = api_key_manager.delete_key(service)
    
    # Assert
    assert result is True
    mock_redis.delete.assert_called_once_with("api_keys:test_service")

def test_list_services(api_key_manager, mock_redis):
    # Arrange
    mock_redis.scan_iter.return_value = [
        b"api_keys:service1",
        b"api_keys:service2"
    ]
    mock_redis.get.side_effect = [
        json.dumps({
            'created_at': datetime.utcnow().isoformat(),
            'last_used': None
        }),
        json.dumps({
            'created_at': datetime.utcnow().isoformat(),
            'last_used': datetime.utcnow().isoformat()
        })
    ]
    
    # Act
    services = api_key_manager.list_services()
    
    # Assert
    assert len(services) == 2
    assert 'service1' in services
    assert 'service2' in services
    assert 'created_at' in services['service1']
    assert 'last_used' in services['service2'] 