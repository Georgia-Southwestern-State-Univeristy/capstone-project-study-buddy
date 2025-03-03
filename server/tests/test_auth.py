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
    def test_signup_success(self, mock_create_token, mock_hash, mock_mongo, mock_user, app, client):
        """Test successful user signup"""
        # Setup mocks
        mock_hash.return_value = "hashed_password"
        mock_create_token.return_value = "test_access_token"
        
        # Mock UserModel validation - this prevents the serialization error
        mock_user_instance = MagicMock()
        mock_user_instance.username = "test_user"
        mock_user_instance.email = "test@example.com"
        mock_user_instance.password = "password123"
        mock_user_instance.preferredLanguage = "en"
        mock_user_instance.profile_picture = "/static/profile_pics/test_user_secure_filename.jpg"
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
        
        # Use Flask's FileStorage to properly mock file upload
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
        
        # Mock file saving operations
        with patch('routes.auth.os.path.join', return_value='/path/to/image.jpg'):
            with patch('routes.auth.secure_filename', return_value='secure_filename.jpg'):
                with patch('builtins.open', mock_open()):
                    with patch('routes.auth.os.makedirs'):  # Ensure makedirs is mocked
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
    
    @patch('routes.auth.UserModel')
    @patch('routes.auth.MongoDBClient')
    def test_signup_existing_user(self, mock_mongo, mock_user, app, client):
        """Test signup with an existing user (username/email)"""
        # Setup mocks
        mock_db = MagicMock()
        mock_mongo.get_client.return_value = MagicMock()
        mock_mongo.get_db_name.return_value = "test_db"
        mock_mongo.get_client.return_value.__getitem__.return_value = mock_db
        # User exists
        mock_db.__getitem__.return_value.find_one.return_value = {'username': 'test_user', 'email': 'test@example.com'}
        
        # Create test data
        data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'Test User',
        }
        
        # Send request
        response = client.post(
            '/user/signup',
            data=data,
            content_type='multipart/form-data'
        )
            
        # Assertions
        assert response.status_code == 409
        response_data = json.loads(response.data)
        assert response_data['error'] == 'User with this username or email already exists'
    
    @patch('routes.auth.validate_email')
    @patch('routes.auth.UserModel')
    @patch('routes.auth.check_password_hash')
    @patch('routes.auth.create_access_token')
    def test_login_success_with_email(self, mock_create_token, mock_check_hash, 
                                     mock_user, mock_validate, client):
        """Test successful login with email"""
        # Setup mocks
        mock_validate.return_value = True  # Valid email
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_id"
        mock_user_instance.password = "hashed_password"
        mock_user_instance.preferredLanguage = "en"
        mock_user.find_by_email.return_value = mock_user_instance
        mock_check_hash.return_value = True  # Password matches
        mock_create_token.return_value = "test_access_token"
        
        # Create test data
        data = {
            'identifier': 'test@example.com',
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
        assert response_data['preferredLanguage'] == 'en'
        
        # Verify mocks were called correctly
        mock_validate.assert_called_once()
        mock_user.find_by_email.assert_called_once_with('test@example.com')
        mock_check_hash.assert_called_once_with('hashed_password', 'password123')
    

    @patch('routes.auth.token_urlsafe')
    def test_google_login(self, mock_token_urlsafe, app, client):
        """Test Google OAuth login redirect"""
        # Mock token_urlsafe to return a predictable value
        mock_token_urlsafe.return_value = "test_nonce"
        
        # Mock the oauth object
        with patch('routes.auth.oauth') as mock_oauth:
            # Set up the google authorize_redirect mock
            mock_google = MagicMock()
            mock_oauth.google = mock_google
            mock_google.authorize_redirect.return_value = "redirect_response"
            
            # Call within request context to avoid session issues
            with app.test_request_context('/auth/google'):
                # Call the route handler directly
                from routes.auth import google_login
                response = google_login()
                
                # Verify the oauth redirect was called
                mock_google.authorize_redirect.assert_called_once()
                
                # Verify the nonce was stored in session
                assert session.get('oauth_nonce') == "test_nonce"
    
    @patch('routes.auth.UserModel')
    @patch('routes.auth.mail')
    def test_request_password_reset(self, mock_mail, mock_user, client):
        """Test password reset request"""
        # Setup mocks
        mock_user_instance = MagicMock()
        mock_user_instance.email = "test@example.com"
        mock_user.find_by_email.return_value = mock_user_instance
        
        # Create test data
        data = {
            'email': 'test@example.com'
        }
        
        # Mock token generation
        with patch('routes.auth.generate_reset_token') as mock_token:
            mock_token.return_value = "reset_token"
            
            # Send request
            response = client.post('/user/request_reset',
                                data=json.dumps(data),
                                content_type='application/json')
            
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['message'] == 'Check your email for the reset password link'
        
        # Verify email was sent
        mock_mail.send.assert_called_once()
    
    @patch('routes.auth.verify_reset_token')
    def test_reset_password(self, mock_verify_token, client):
        """Test password reset with valid token"""
        # Setup mocks
        mock_user = MagicMock()
        mock_verify_token.return_value = mock_user
        
        # Create test data
        data = {
            'password': 'new_password123'
        }
        
        # Send request
        response = client.post('/user/reset_password/valid_token',
                            data=json.dumps(data),
                            content_type='application/json')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['message'] == 'Password has been reset successfully'
        
        # Verify password was updated
        mock_user.update_password.assert_called_once()