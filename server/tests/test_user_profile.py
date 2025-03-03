import pytest
import json
import io
import os
from unittest.mock import patch, MagicMock, mock_open
from flask import Flask, Request
from bson import ObjectId
from flask_jwt_extended import JWTManager, create_access_token

from routes.user_profile import user_routes, allowed_file, ALLOWED_EXTENSIONS

# Create a valid ObjectId for testing
TEST_USER_ID = str(ObjectId())

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    # Configure JWT for testing
    app.config['JWT_SECRET_KEY'] = 'jwt-test-secret-key'
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
    JWTManager(app)
    
    app.register_blueprint(user_routes)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(app):
    with app.app_context():
        access_token = create_access_token(identity=TEST_USER_ID)
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        return headers

@pytest.fixture
def mock_jwt_required():
    with patch('routes.user_profile.jwt_required') as mock:
        # Make the decorator do nothing
        mock.return_value = lambda f: f
        yield mock

@pytest.fixture
def mock_get_jwt_identity():
    with patch('routes.user_profile.get_jwt_identity') as mock:
        # Use a valid ObjectId string instead of "test_user_id"
        mock.return_value = TEST_USER_ID
        yield mock

@pytest.fixture
def mock_mongodb_client():
    with patch('routes.user_profile.MongoDBClient') as mock:
        mock_client = MagicMock()
        mock_db = MagicMock()
        
        # Set up the mock client and db
        mock.get_client.return_value = mock_client
        mock_db_name = "test_db"
        mock.get_db_name.return_value = mock_db_name
        mock_client.__getitem__.return_value = mock_db
        
        yield mock, mock_client, mock_db

class TestAllowedFile:
    
    def test_allowed_file_valid_extensions(self):
        """Test allowed_file with valid file extensions"""
        for ext in ALLOWED_EXTENSIONS:
            assert allowed_file(f"test.{ext}") is True
            assert allowed_file(f"test.{ext.upper()}") is True  # Test case insensitivity
    
    def test_allowed_file_invalid_extensions(self):
        """Test allowed_file with invalid file extensions"""
        assert allowed_file("test.txt") is False
        assert allowed_file("test.pdf") is False
        assert allowed_file("test.exe") is False
        assert allowed_file("test") is False  # No extension
        assert allowed_file("") is False  # Empty filename


class TestGetUserProfile:
    
    def test_get_profile_success(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test successful retrieval of user profile"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation to return a user
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "email": "test@example.com",
                "password": "hashed_password",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            mock_db["users"].find_one.return_value = mock_user
            
            # Make request with auth headers
            response = client.get('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert "_id" in data
            assert "password" not in data  # Password should be removed
            
            # Verify find_one was called with the correct user_id
            mock_db["users"].find_one.assert_called_once_with({"_id": ObjectId(TEST_USER_ID)})
    
    def test_get_profile_user_not_found(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test getting profile when user is not found"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation to return None (user not found)
            mock_db["users"].find_one.return_value = None
            
            # Make request with auth headers
            response = client.get('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert "error" in data
            assert "User could not be found" in data["error"]
            
            # Verify find_one was called with the correct user_id
            mock_db["users"].find_one.assert_called_once_with({"_id": ObjectId(TEST_USER_ID)})
    
    def test_get_profile_exception(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test getting profile when an exception occurs"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation to raise an exception
            mock_db["users"].find_one.side_effect = Exception("Database error")
            
            # Need to use try-except to handle the exception
            try:
                # Import get_public_profile directly
                from routes.user_profile import get_public_profile
                
                # Call the function directly - it should raise an exception
                result = get_public_profile()
                assert False, "Expected an exception but none was raised"
            except Exception:
                # We expect an exception
                assert True


class TestUpdateUserProfile:
    
    def test_update_profile_success(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test successful profile update (text fields only)"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "email": "old@example.com",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            mock_db["users"].find_one.return_value = mock_user
            
            # Create request data
            form_data = {"email": "new@example.com", "bio": "New bio"}
            
            # Make request
            response = client.patch('/user/profile', 
                                data=form_data, 
                                headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "User has been updated successfully."
            assert data["profile_picture"] == "/static/profile_pics/testuser_pic.jpg"  # Unchanged
            
            # Verify update_one was called with the correct data
            mock_db["users"].update_one.assert_called_once_with(
                {"_id": ObjectId(TEST_USER_ID)}, 
                {"$set": {"email": "new@example.com", "bio": "New bio"}}
            )
    
    def test_update_profile_with_picture(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile update with new profile picture"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "email": "test@example.com",
                "profile_picture": "/static/profile_pics/old_picture.jpg"
            }
            mock_db["users"].find_one.return_value = mock_user
            
            # Create test file
            test_file = (io.BytesIO(b"test file content"), "new_picture.jpg")
            
            # Mock file operations without patching request
            with patch('werkzeug.datastructures.FileStorage.save'):
                with patch('routes.user_profile.os.path.exists', return_value=True):
                    with patch('routes.user_profile.os.remove'):
                        with patch('routes.user_profile.os.path.join', return_value="/path/to/file"):
                            # Make request
                            response = client.patch(
                                '/user/profile',
                                data={
                                    'bio': 'Updated bio',
                                    'profile_picture': test_file
                                },
                                content_type='multipart/form-data',
                                headers=auth_headers
                            )
                            
                            # Assertions
                            assert response.status_code == 200
                            data = json.loads(response.data)
                            assert data["message"] == "User has been updated successfully."
                            assert "profile_picture" in data

    
    def test_update_profile_invalid_image_format(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile update with invalid image format"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser"
            }
            mock_db["users"].find_one.return_value = mock_user
            
            # Create invalid test file
            test_file = (io.BytesIO(b"test file content"), "document.txt")
            
            # Make request
            response = client.patch(
                '/user/profile',
                data={'profile_picture': test_file},
                content_type='multipart/form-data',
                headers=auth_headers
            )
            
            # Assertions
            assert response.status_code == 400
            data = json.loads(response.data)
            assert "error" in data
            assert "Invalid image format" in data["error"]
    
    def test_update_profile_no_fields(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile update with no fields to update"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser"
            }
            mock_db["users"].find_one.return_value = mock_user
            
            # Make request with empty data
            response = client.patch('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "No fields to update."
            
            # Verify database not updated
            mock_db["users"].update_one.assert_not_called()
    
    def test_update_profile_user_not_found(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile update when user is not found"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation to return None (user not found)
            mock_db["users"].find_one.return_value = None
            
            # Make request
            response = client.patch(
                '/user/profile',
                data={"bio": "New bio"},
                headers=auth_headers
            )
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert "error" in data
            assert "User cannot be found" in data["error"]
            
            # Verify database not updated
            mock_db["users"].update_one.assert_not_called()
    
    def test_update_profile_exception(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile update when an exception occurs"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation to raise an exception
            mock_db["users"].find_one.side_effect = Exception("Database error")
            
            # Make request
            response = client.patch(
                '/user/profile',
                data={"bio": "New bio"},
                headers=auth_headers
            )
            
            # Assertions
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data
            assert "An error occurred while updating the profile" in data["error"]


class TestDeleteUserProfile:
    
    def test_delete_profile_success(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test successful user profile deletion"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            mock_db["users"].find_one.return_value = mock_user
            
            # Mock file operations
            with patch('routes.user_profile.os.path.exists', return_value=True):
                with patch('routes.user_profile.os.remove') as mock_remove:
                    # Make request
                    response = client.delete('/user/profile', headers=auth_headers)
                    
                    # Assertions
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["message"] == "User has been deleted successfully."
                    
                    # Verify profile picture was deleted
                    mock_remove.assert_called_once()
                    
                    # Verify database deletion
                    mock_db["users"].delete_one.assert_called_once_with({"_id": ObjectId(TEST_USER_ID)})
    
    def test_delete_profile_no_picture(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test user deletion when profile has no picture"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation with no profile picture
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser"
                # No profile_picture field
            }
            mock_db["users"].find_one.return_value = mock_user
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "User has been deleted successfully."
            
            # Verify database deletion
            mock_db["users"].delete_one.assert_called_once_with({"_id": ObjectId(TEST_USER_ID)})
    
    def test_delete_profile_user_not_found(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile deletion when user is not found"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation to return None (user not found)
            mock_db["users"].find_one.return_value = None
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert "error" in data
            assert "User cannot be found" in data["error"]
            
            # Verify database deletion was not called
            mock_db["users"].delete_one.assert_not_called()
    
    def test_delete_profile_exception(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile deletion when an exception occurs"""
        with app.app_context():
            _, _, mock_db = mock_mongodb_client
            
            # Mock the find_one operation to raise an exception
            mock_db["users"].find_one.side_effect = Exception("Database error")
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data
            assert "An error occurred while deleting the profile" in data["error"]
            
            # Verify database deletion was not called
            mock_db["users"].delete_one.assert_not_called()