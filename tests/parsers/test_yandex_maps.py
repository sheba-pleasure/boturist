import pytest
from unittest.mock import Mock, patch
from parsers.maps.yandex_maps import YandexMapsParser, parse_yandex_maps_reviews

@pytest.fixture
async def mock_playwright():
    with patch('playwright.async_api.async_playwright') as mock:
        mock_browser = Mock()
        mock_page = Mock()
        
        # Setup mock responses
        mock_page.evaluate.return_value = [
            {
                'text': 'Great service!',
                'rating': '5',
                'author': 'John Doe',
                'date': '01.01.2024'
            }
        ]
        
        mock_browser.new_page.return_value = mock_page
        mock.return_value.chromium.launch.return_value = mock_browser
        yield mock

@pytest.mark.asyncio
async def test_get_reviews(mock_playwright):
    # Arrange
    parser = await YandexMapsParser()
    
    # Act
    reviews = await parser.get_reviews("https://yandex.ru/maps/org/123")
    
    # Assert
    assert len(reviews) == 1
    assert reviews[0]['text'] == 'Great service!'
    assert reviews[0]['rating'] == '5'

@pytest.mark.asyncio
@pytest.mark.integration
@patch('parsers.maps.yandex_maps.save_reviews_to_mongodb')
async def test_parse_yandex_maps_reviews_task(mock_save_to_mongodb, mock_playwright):
    # Arrange
    business_url = "https://yandex.ru/maps/org/123"
    
    # Act
    await parse_yandex_maps_reviews(business_url)
    
    # Assert
    mock_save_to_mongodb.assert_called_once_with(
        [
            {
                'text': 'Great service!',
                'rating': '5',
                'author': 'John Doe',
                'date': '01.01.2024'
            }
        ],
        business_url
    )

@pytest.mark.asyncio
async def test_parser_cleanup(mock_playwright):
    # Arrange
    parser = await YandexMapsParser()
    
    # Act
    await parser.close()
    
    # Assert
    mock_playwright.return_value.stop.assert_called_once()
    mock_playwright.return_value.chromium.launch.return_value.close.assert_called_once() 