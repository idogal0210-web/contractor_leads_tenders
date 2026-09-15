import unittest
from unittest.mock import patch, MagicMock
from src.validation import validate_source_url
from core.db.models import UrlValidationStatus

class TestValidation(unittest.TestCase):
    @patch('src.validation.requests.get')
    def test_validate_source_url_valid(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = 'https://example.com/final'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.content = b"<html><body>Some text</body></html>"
        mock_get.return_value = mock_response

        status, final_url = validate_source_url('https://example.com/initial')
        
        self.assertEqual(status, UrlValidationStatus.VALID)
        self.assertEqual(final_url, 'https://example.com/final')

    @patch('src.validation.requests.get')
    def test_validate_source_url_invalid_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.url = 'https://example.com/404'
        mock_get.return_value = mock_response

        status, final_url = validate_source_url('https://example.com/missing')
        
        self.assertEqual(status, UrlValidationStatus.INVALID)
        self.assertEqual(final_url, 'https://example.com/404')

    @patch('src.validation.requests.get')
    def test_validate_source_url_requires_auth(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = 'https://example.com/login'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.content = b"<html><body><input type='password' name='pass'/></body></html>"
        mock_get.return_value = mock_response

        status, final_url = validate_source_url('https://example.com/forum')
        
        self.assertEqual(status, UrlValidationStatus.REQUIRES_AUTH)
        self.assertEqual(final_url, 'https://example.com/login')

    @patch('src.validation.requests.get')
    def test_validate_source_url_exception(self, mock_get):
        mock_get.side_effect = Exception("Connection error")

        status, final_url = validate_source_url('https://example.com/error')
        
        self.assertEqual(status, UrlValidationStatus.INVALID)
        self.assertEqual(final_url, 'https://example.com/error')

if __name__ == '__main__':
    unittest.main()
