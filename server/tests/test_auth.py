import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from flask import Flask, session
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId
from datetime import timedelta
from routes.auth import auth_routes, UPLOAD_FOLDER, allowed_file
from flask_jwt_extended import JWTManager

# Create a Flask test app
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    app.config['MAIL_DEFAULT_SENDER'] = 'test@example.com'
    
    # Configure JWT for testing
    app.config['JWT_SECRET_KEY'] = 'test_jwt_secret'
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    jwt = JWTManager(app)
    
    app.register_blueprint(auth_routes)
    
    # Configure session for testing
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    
    # Setup application context
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

class TestAuthRoutes:
    
    def test_allowed_file(self):
        """Test allowed_file function"""
        assert allowed_file('test.jpg') is True
        assert allowed_file('test.png') is True
        assert allowed_file('test.gif') is True
        assert allowed_file('test.jpeg') is True
        assert allowed_file('test.txt') is False
        assert allowed_file('test') is False
    
    @patch('routes.auth.UserModel')
    @patch('routes.auth.MongoDBClient')
    @patch('routes.auth.generate_password_hash')
    @patch('routes.auth.create_access_token')
    @patch('routes.auth.AzureBlobService')  # Mock AzureBlobService instead of local file operations
    def test_signup_success(self, mock_azure_blob, mock_create_token, mock_hash, mock_mongo, mock_user, app, client):
        """Test successful user signup"""
        # Setup mocks
        mock_hash.return_value = "hashed_password"
        mock_create_token.return_value = "test_access_token"
        
        # Mock AzureBlobService upload_file to return a test URL
        mock_azure_instance = MagicMock()
        mock_azure_instance.upload_file.return_value = "https://testblob.test/container/test_user_image.jpg"
        mock_azure_blob.return_value = mock_azure_instance
        
        # Mock UserModel validation
        mock_user_instance = MagicMock()
        mock_user_instance.username = "test_user"
        mock_user_instance.email = "test@example.com"
        mock_user_instance.password = "password123"
        mock_user_instance.preferredLanguage = "en"
        mock_user_instance.profile_picture = "https://testblob.test/container/test_user_image.jpg"
        mock_user.return_value = mock_user_instance
        
        # Mock MongoDB client and operations
        mock_db = MagicMock()
        mock_mongo.get_client.return_value = MagicMock()
        mock_mongo.get_db_name.return_value = "test_db"
        mock_mongo.get_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = None  # User doesn't exist
        mock_db.__getitem__.return_value.insert_one.return_value.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        
        # Create test data with file
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        test_file = FileStorage(
            stream=BytesIO(b"test image content"),
            filename="test.jpg",
            content_type="image/jpeg",
        )
        
        data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'Test User',
        }
        
        # Send request with multipart form data
        data['profile_picture'] = test_file
        response = client.post(
            '/user/signup',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assertions
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert 'access_token' in response_data
        assert response_data['message'] == 'User registered successfully'
        assert response_data['preferredLanguage'] == 'en'
        assert response_data['profile_picture'] == "https://testblob.test/container/test_user_image.jpg"
        
        # Verify Azure blob service was called with correct parameters
        mock_azure_instance.upload_file.assert_called_once()
        
    @patch('routes.auth.UserModel')
    @patch('routes.auth.MongoDBClient')
    @patch('routes.auth.AzureBlobService')
    def test_signup_invalid_file(self, mock_azure_blob, mock_mongo, mock_user, app, client):
        """Test signup with an invalid file type"""
        # Create test data with invalid file
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        test_file = FileStorage(
            stream=BytesIO(b"test document content"),
            filename="test.txt",
            content_type="text/plain",
        )
        
        data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'Test User',
        }
        
        # Send request with invalid file
        data['profile_picture'] = test_file
        response = client.post(
            '/user/signup',
            data=data,
            content_type='multipart/form-data'
        )
            
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['error'] == 'Invalid image format'
    
    @patch('routes.auth.UserModel')
    @patch('routes.auth.MongoDBClient')
    @patch('routes.auth.AzureBlobService')
    @patch('routes.auth.generate_password_hash')
    def test_signup_without_profile_picture(self, mock_hash, mock_azure_blob, mock_mongo, mock_user, app, client):
        """Test signup without a profile picture"""
        # Setup mocks
        mock_hash.return_value = "hashed_password"
        mock_db = MagicMock()
        mock_mongo.get_client.return_value = MagicMock()
        mock_mongo.get_db_name.return_value = "test_db"
        mock_mongo.get_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = None
        mock_db.__getitem__.return_value.insert_one.return_value.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        
        # Mock UserModel validation
        mock_user_instance = MagicMock()
        mock_user_instance.username = "test_user"
        mock_user_instance.email = "test@example.com"
        mock_user_instance.password = "password123"
        mock_user_instance.preferredLanguage = "en"
        mock_user_instance.profile_picture = None
        mock_user.return_value = mock_user_instance
        
        # Create test data without file
        data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'Test User',
        }
        
        # Send request without profile picture
        response = client.post(
            '/user/signup',
            data=data,
            content_type='multipart/form-data'
        )
            
        # Assertions
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['profile_picture'] is None
    
    @patch('routes.auth.AzureBlobService')
    def test_azure_blob_upload_failure(self, mock_azure_blob, app, client):
        """Test handling of Azure Blob upload failure"""
        # Setup Azure Blob Service to raise exception
        mock_azure_instance = MagicMock()
        mock_azure_instance.upload_file.side_effect = Exception("Azure Storage connection error")
        mock_azure_blob.return_value = mock_azure_instance
        
        # Create test data with file
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        test_file = FileStorage(
            stream=BytesIO(b"test image content"),
            filename="test.jpg",
            content_type="image/jpeg",
        )
        
        data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'Test User',
            'profile_picture': test_file
        }
        
        # Send request
        response = client.post(
            '/user/signup',
            data=data,
            content_type='multipart/form-data'
        )
            
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "Azure Storage connection error" in response_data.get('error', '')

    @patch('routes.auth.UserModel')
    @patch('routes.auth.create_access_token')
    def test_login_with_username(self, mock_create_token, mock_user, client):
        """Test successful login with username"""
        # Setup mocks
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_id"
        mock_user_instance.password = "hashed_password"
        mock_user_instance.preferredLanguage = "es"
        mock_user.find_by_username.return_value = mock_user_instance
        mock_create_token.return_value = "test_access_token"
        
        # Mock password check
        with patch('routes.auth.check_password_hash', return_value=True):
            # Create test data
            data = {
                'identifier': 'test_user',  # Username instead of email
                'password': 'password123'
            }
            
            # Send request
            response = client.post('/user/login', 
                                data=json.dumps(data), 
                                content_type='application/json')
            
            # Assertions
            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert response_data['access_token'] == 'test_access_token'
            assert response_data['userId'] == 'user_id'
            assert response_data['preferredLanguage'] == 'es'
            
            # Verify mocks were called correctly
            mock_user.find_by_username.assert_called_once_with('test_user')

    @patch('routes.auth.verify_reset_token')
    def test_reset_password_invalid_token(self, mock_verify_token, client):
        """Test password reset with invalid token"""
        # Setup mocks
        mock_verify_token.return_value = None  # Token is invalid
        
        # Create test data
        data = {
            'password': 'new_password123'
        }
        
        # Send request
        response = client.post('/user/reset_password/invalid_token',
                            data=json.dumps(data),
                            content_type='application/json')
        
        # Assertions
        assert response.status_code == 403
        response_data = json.loads(response.data)
        assert response_data['error'] == 'Invalid or expired token'

    @patch('routes.auth.oauth')
    @patch('routes.auth.token_urlsafe')
    @patch('routes.auth.UserModel')
    @patch('routes.auth.MongoDBClient')
    @patch('routes.auth.create_access_token')
    def test_google_callback_new_user(self, mock_create_token, mock_mongo, mock_user, 
                                     mock_token_urlsafe, mock_oauth, app, client):
        """Test Google OAuth callback with a new user"""
        with app.test_request_context():
            # Setup session
            session['oauth_nonce'] = 'test_nonce'
            
            # Mock token and user info
            mock_token = {
                'id_token': 'test_id_token',
                'access_token': 'test_access_token'
            }
            mock_oauth.google.authorize_access_token.return_value = mock_token
            
            mock_user_info = {
                'sub': 'google_user_id',
                'email': 'googleuser@example.com',
                'name': 'Google User',
                'picture': 'https://example.com/profile.jpg'
            }
            mock_oauth.google.parse_id_token.return_value = mock_user_info
            
            # Mock user doesn't exist yet
            mock_user.find_by_email.return_value = None
            
            # Mock MongoDB operations for new user creation
            mock_db = MagicMock()
            mock_mongo.get_client.return_value = MagicMock()
            mock_mongo.get_db_name.return_value = "test_db"
            mock_mongo.get_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value.insert_one.return_value.inserted_id = ObjectId("507f1f77bcf86cd799439011")
            
            # Mock token creation
            mock_create_token.return_value = "test_access_token"
            
            # Mock environment variable
            with patch.dict('os.environ', {'BASE_URL': 'http://localhost:4200'}):
                # Call the handler directly
                from routes.auth import google_callback
                response = google_callback()
                
                # Verify it's a redirect
                assert response.status_code == 302
                assert 'http://localhost:4200/auth/auth-callback?token=test_access_token' in response.location
                
                # Verify new user was created
                mock_db.__getitem__.return_value.insert_one.assert_called_once()