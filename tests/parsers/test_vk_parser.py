import pytest
from unittest.mock import Mock, patch
from parsers.social_media.vk_parser import VKParser, parse_vk_group

@pytest.fixture
def mock_vk_api():
    with patch('vk_api.VkApi') as mock:
        mock_api = Mock()
        mock.return_value.get_api.return_value = mock_api
        yield mock_api

@pytest.fixture
def vk_parser(mock_vk_api):
    return VKParser("test_token")

def test_get_group_posts(vk_parser, mock_vk_api):
    # Arrange
    mock_vk_api.wall.get.return_value = {
        'items': [
            {'id': 1, 'text': 'Test post 1'},
            {'id': 2, 'text': 'Test post 2'}
        ]
    }
    
    # Act
    posts = vk_parser.get_group_posts("test_group")
    
    # Assert
    assert len(posts) == 2
    assert posts[0]['text'] == 'Test post 1'
    mock_vk_api.wall.get.assert_called_once_with(
        owner_id="test_group",
        count=100
    )

def test_get_comments(vk_parser, mock_vk_api):
    # Arrange
    mock_vk_api.wall.getComments.return_value = {
        'items': [
            {'id': 1, 'text': 'Test comment 1'},
            {'id': 2, 'text': 'Test comment 2'}
        ]
    }
    
    # Act
    comments = vk_parser.get_comments("test_group", 1)
    
    # Assert
    assert len(comments) == 2
    assert comments[0]['text'] == 'Test comment 1'
    mock_vk_api.wall.getComments.assert_called_once_with(
        owner_id="test_group",
        post_id=1,
        need_likes=1,
        count=100
    )

@pytest.mark.integration
@patch('parsers.social_media.vk_parser.save_to_mongodb')
def test_parse_vk_group_task(mock_save_to_mongodb, mock_vk_api):
    # Arrange
    mock_vk_api.wall.get.return_value = {
        'items': [{'id': 1, 'text': 'Test post'}]
    }
    mock_vk_api.wall.getComments.return_value = {
        'items': [{'id': 1, 'text': 'Test comment'}]
    }
    
    # Act
    parse_vk_group("test_group", "test_token")
    
    # Assert
    mock_save_to_mongodb.assert_called_once_with(
        {'id': 1, 'text': 'Test post'},
        [{'id': 1, 'text': 'Test comment'}]
    ) 