import pytest
import json
import os
from unittest.mock import patch, MagicMock
from flask import Flask
from routes.translator import translator_routes





@pytest.fixture
def app():
    """Create and configure a Flask app for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(translator_routes)
    
    return app

@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return app.test_client()

@pytest.fixture
def mock_env_variables():
    """Mock environment variables for Azure Translator"""
    with patch.dict(os.environ, {
        'AZURE_TRANSLATOR_KEY': 'test_api_key',
        'AZURE_TRANSLATOR_ENDPOINT': 'https://api.cognitive.microsofttranslator.com',
        'AZURE_TRANSLATOR_REGION': 'eastus'
    }):
        yield

class TestTranslatorRoutes:

    @patch('routes.translator.requests.post')
    def test_translate_success(self, mock_post, client, mock_env_variables):
        """Test successful translation"""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "translations": [
                    {
                        "text": "Hola",
                        "to": "es"
                    }
                ]
            },
            {
                "translations": [
                    {
                        "text": "Mundo",
                        "to": "es"
                    }
                ]
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Test data
        data = {
            "texts": ["Hello", "World"],
            "target_language": "es"
        }

        # Make request
        response = client.post(
            '/translate',
            data=json.dumps(data),
            content_type='application/json'
        )

        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "translations" in response_data
        assert response_data["translations"] == ["Hola", "Mundo"]

        # Verify mock was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['params']['to'] == 'es'
        assert kwargs['json'] == [{'text': 'Hello'}, {'text': 'World'}]
        assert 'headers' in kwargs

    def test_translate_missing_inputs(self, client):
        """Test translation with missing inputs"""
        # Test missing texts
        data = {
            "target_language": "es"
        }
        response = client.post(
            '/translate',
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code == 400
        assert b"Missing texts or target_language" in response.data

        # Test missing target language
        data = {
            "texts": ["Hello"]
        }
        response = client.post(
            '/translate',
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code == 400
        assert b"Missing texts or target_language" in response.data

        # Test empty request
        response = client.post(
            '/translate',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
        assert b"Missing texts or target_language" in response.data

    def test_translate_missing_env_variables(self, client):
        """Test translation with missing environment variables"""
        # Test data
        data = {
            "texts": ["Hello"],
            "target_language": "es"
        }
        
        # Without mocking env variables, they should be None
        with patch.dict(os.environ, {
            'AZURE_TRANSLATOR_KEY': '',
            'AZURE_TRANSLATOR_ENDPOINT': ''
        }, clear=True):
            response = client.post(
                '/translate',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            assert response.status_code == 500
            assert b"Server configuration error" in response.data

    

    @patch('routes.translator.requests.post')
    def test_translate_empty_text_list(self, mock_post, client, mock_env_variables):
        """Test translation with empty text list"""
        # Test data
        data = {
            "texts": [],
            "target_language": "es"
        }

        # Make request
        response = client.post(
            '/translate',
            data=json.dumps(data),
            content_type='application/json'
        )

        # Since empty texts list is falsy, it should return 400
        assert response.status_code == 400
        assert b"Missing texts or target_language" in response.data

    @patch('routes.translator.requests.post')
    def test_translate_multiple_languages(self, mock_post, client, mock_env_variables):
        """Test translating to multiple languages"""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "translations": [
                    {
                        "text": "Bonjour",
                        "to": "fr"
                    }
                ]
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Test data for French
        data = {
            "texts": ["Hello"],
            "target_language": "fr"
        }

        # Make request
        response = client.post(
            '/translate',
            data=json.dumps(data),
            content_type='application/json'
        )

        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data["translations"] == ["Bonjour"]

        # Verify correct language was requested
        args, kwargs = mock_post.call_args
        assert kwargs['params']['to'] == 'fr'

    