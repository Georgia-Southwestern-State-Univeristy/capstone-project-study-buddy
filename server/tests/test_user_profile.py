import pytest
import json
import io
import os
from unittest.mock import patch, MagicMock, mock_open, call
from flask import Flask
from bson import ObjectId
from flask_jwt_extended import JWTManager, create_access_token

from routes.user_profile import user_routes, allowed_file, ALLOWED_EXTENSIONS

# Create a valid ObjectId for testing
TEST_USER_ID = str(ObjectId())
TEST_OBJECT_ID = ObjectId(TEST_USER_ID)  # Create an ObjectId instance for comparison

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
        
        # Create separate dictionary for users/journeys collections to avoid reference issues
        users_collection = MagicMock()
        journeys_collection = MagicMock()
        mock_db.__getitem__.side_effect = lambda x: users_collection if x == "users" else journeys_collection
        
        yield mock, mock_client, mock_db, users_collection, journeys_collection

@pytest.fixture
def mock_azure_blob_service():
    with patch('routes.user_profile.AzureBlobService') as mock:
        # Create a mock instance for the service
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock the blob operations
        mock_instance.upload_file.return_value = "https://teststorage.blob.core.windows.net/users/test-profile.jpg"
        mock_instance.delete_blob.return_value = True
        
        yield mock_instance

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
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation to return a user as a dictionary
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "email": "test@example.com",
                "password": "hashed_password",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            users_collection.find_one.return_value = mock_user
            
            # Mock user_journey
            mock_journey = {
                "_id": ObjectId(),
                "user_id": TEST_USER_ID,
                "fieldOfStudy": "Computer Science",
                "student_goals": ["Learn Python", "Build Web Apps"]
            }
            journeys_collection.find_one.return_value = mock_journey
            
            # Make request with auth headers
            response = client.get('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert "_id" in data
            assert "password" not in data  # Password should be removed
            assert "user_journey" in data
            assert data["user_journey"]["fieldOfStudy"] == "Computer Science"
            
            # Verify find_one was called with the correct user_id
            users_collection.find_one.assert_called_once_with({"_id": TEST_OBJECT_ID})
    
    def test_get_profile_user_not_found(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test getting profile when user is not found"""
        with app.app_context():
            _, _, _, users_collection, _ = mock_mongodb_client
            
            # Mock the find_one operation to return None (user not found)
            users_collection.find_one.return_value = None
            
            # Make request with auth headers
            response = client.get('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert "error" in data
            assert "User could not be found" in data["error"]
            
            # Verify find_one was called with the correct user_id
            users_collection.find_one.assert_called_once_with({"_id": TEST_OBJECT_ID})
    
    def test_get_profile_no_user_journey(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test getting profile when user has no journey"""
        with app.app_context():
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation to return a user
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "email": "test@example.com",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            users_collection.find_one.return_value = mock_user
            
            # Mock no user_journey (return None)
            journeys_collection.find_one.return_value = None
            
            # Make request with auth headers
            response = client.get('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "username" in data
            assert "user_journey" not in data
            
            # Verify find_one was called with the correct user_id
            users_collection.find_one.assert_called_once_with({"_id": TEST_OBJECT_ID})


class TestUpdateUserProfile:
    
    def test_update_profile_success(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test successful profile update (text fields only)"""
        with app.app_context():
            _, _, _, users_collection, _ = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "email": "old@example.com",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            users_collection.find_one.return_value = mock_user
            
            # Create request data
            form_data = {"email": "new@example.com", "bio": "New bio"}
            
            # Make request with JSON data
            response = client.patch('/user/profile', 
                                json=form_data,
                                headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "Profile updated successfully"
            
            # Verify update_one was called with the correct data
            users_collection.update_one.assert_called_once_with(
                {"_id": TEST_OBJECT_ID}, 
                {"$set": {"email": "new@example.com", "bio": "New bio"}}
            )
    
    def test_update_profile_with_picture(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client, mock_azure_blob_service):
        """Test profile update with new profile picture"""
        with app.app_context():
            _, _, _, users_collection, _ = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "email": "test@example.com",
                "profile_picture": "/static/profile_pics/old_picture.jpg"
            }
            users_collection.find_one.return_value = mock_user
            
            # Create test file
            test_file = (io.BytesIO(b"test file content"), "new_picture.jpg")
            
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
            assert data["message"] == "Profile updated successfully"
            assert "profile_picture" in data
            assert data["profile_picture"] == "https://teststorage.blob.core.windows.net/users/test-profile.jpg"
            
            # Verify blob service was called correctly
            mock_azure_blob_service.delete_blob.assert_called_once_with("/static/profile_pics/old_picture.jpg")
            mock_azure_blob_service.upload_file.assert_called_once()
    
    def test_update_profile_invalid_image_format(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client, mock_azure_blob_service):
        """Test profile update with invalid image format"""
        with app.app_context():
            _, _, _, users_collection, _ = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser"
            }
            users_collection.find_one.return_value = mock_user
            
            # Create invalid test file
            test_file = (io.BytesIO(b"test file content"), "document.txt")
            
            # Make request
            response = client.patch(
                '/user/profile',
                data={
                    'profile_picture': test_file
                },
                content_type='multipart/form-data',
                headers=auth_headers
            )
            
            # Assertions
            assert response.status_code == 400
            data = json.loads(response.data)
            assert "error" in data
            assert "Invalid image format" in data["error"]
            
            # Verify blob service was not called
            mock_azure_blob_service.upload_file.assert_not_called()
    
    def test_update_profile_no_fields(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile update with no fields to update"""
        with app.app_context():
            _, _, _, users_collection, _ = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser"
            }
            users_collection.find_one.return_value = mock_user
            
            # Make request with empty JSON
            response = client.patch('/user/profile', json={}, headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "No fields to update."
            
            # Verify database not updated
            users_collection.update_one.assert_not_called()
    
    def test_update_profile_user_not_found(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile update when user is not found"""
        with app.app_context():
            _, _, _, users_collection, _ = mock_mongodb_client
            
            # Mock the find_one operation to return None (user not found)
            users_collection.find_one.return_value = None
            
            # Make request
            response = client.patch(
                '/user/profile',
                json={"bio": "New bio"},
                headers=auth_headers
            )
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert "error" in data
            assert "User not found" in data["error"]
            
            # Verify database not updated
            users_collection.update_one.assert_not_called()
            
    def test_update_journey_field(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test updating a journey-specific field"""
        with app.app_context():
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser"
            }
            users_collection.find_one.return_value = mock_user
            
            # Make request with journey field
            journey_data = {"mental_health_concerns": ["stress", "anxiety"]}
            response = client.patch(
                '/user/profile',
                json=journey_data,
                headers=auth_headers
            )
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "Profile updated successfully"
            
            # Verify only journeys collection was updated
            journeys_collection.update_one.assert_called_once_with(
                {"user_id": TEST_USER_ID},
                {"$set": {"mental_health_concerns": ["stress", "anxiety"]}},
                upsert=True
            )
            users_collection.update_one.assert_not_called()
    
    def test_update_field_of_study(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test updating fieldOfStudy which should update both user and journey"""
        with app.app_context():
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "fieldOfStudy": "History"
            }
            users_collection.find_one.return_value = mock_user
            
            # Make request to update fieldOfStudy
            response = client.patch(
                '/user/profile',
                json={"fieldOfStudy": "Computer Science"},
                headers=auth_headers
            )
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "Profile updated successfully"
            
            # Verify both collections were updated with correct queries
            users_collection.update_one.assert_called_once_with(
                {"_id": TEST_OBJECT_ID}, 
                {"$set": {"fieldOfStudy": "Computer Science"}}
            )
            journeys_collection.update_one.assert_called_once_with(
                {"user_id": TEST_USER_ID},
                {"$set": {"fieldOfStudy": "Computer Science"}},
                upsert=True
            )


class TestDeleteUserProfile:
    
    def test_delete_profile_success(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client, mock_azure_blob_service):
        """Test successful user profile deletion"""
        with app.app_context():
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            users_collection.find_one.return_value = mock_user
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "User has been deleted successfully."
            
            # Verify profile picture was deleted
            mock_azure_blob_service.delete_blob.assert_called_once_with("/static/profile_pics/testuser_pic.jpg")
            
            # Verify database deletion for both collections with correct queries
            users_collection.delete_one.assert_called_once_with({"_id": TEST_OBJECT_ID})
            journeys_collection.delete_one.assert_called_once_with({"user_id": TEST_USER_ID})
    
    def test_delete_profile_no_picture(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client, mock_azure_blob_service):
        """Test user deletion when profile has no picture"""
        with app.app_context():
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation with no profile picture
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser"
                # No profile_picture field
            }
            users_collection.find_one.return_value = mock_user
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "User has been deleted successfully."
            
            # Verify blob deletion was not called
            mock_azure_blob_service.delete_blob.assert_not_called()
            
            # Verify database deletion with correct queries
            users_collection.delete_one.assert_called_once_with({"_id": TEST_OBJECT_ID})
            journeys_collection.delete_one.assert_called_once_with({"user_id": TEST_USER_ID})
    
    def test_delete_profile_user_not_found(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client):
        """Test profile deletion when user is not found"""
        with app.app_context():
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation to return None (user not found)
            users_collection.find_one.return_value = None
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert "error" in data
            assert "User not found" in data["error"]
            
            # Verify database deletion was not called
            users_collection.delete_one.assert_not_called()
            journeys_collection.delete_one.assert_not_called()
    
    def test_delete_profile_blob_exception(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client, mock_azure_blob_service):
        """Test profile deletion when blob deletion fails but user deletion proceeds"""
        with app.app_context():
            _, _, _, users_collection, journeys_collection = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            users_collection.find_one.return_value = mock_user
            
            # Make blob deletion fail
            mock_azure_blob_service.delete_blob.side_effect = Exception("Blob not found")
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "User has been deleted successfully."
            
            # Verify database deletion still succeeded
            users_collection.delete_one.assert_called_once_with({"_id": TEST_OBJECT_ID})
            journeys_collection.delete_one.assert_called_once_with({"user_id": TEST_USER_ID})
    
    def test_delete_profile_database_exception(self, app, client, auth_headers, mock_jwt_required, mock_get_jwt_identity, mock_mongodb_client, mock_azure_blob_service):
        """Test profile deletion when database operation fails"""
        with app.app_context():
            _, _, _, users_collection, _ = mock_mongodb_client
            
            # Mock the find_one operation
            mock_user = {
                "_id": ObjectId(),
                "username": "testuser",
                "profile_picture": "/static/profile_pics/testuser_pic.jpg"
            }
            users_collection.find_one.return_value = mock_user
            
            # Make database deletion fail
            users_collection.delete_one.side_effect = Exception("Database error")
            
            # Make request
            response = client.delete('/user/profile', headers=auth_headers)
            
            # Assertions
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data
            assert "An error occurred" in data["error"]
            
            # Verify blob was attempted to be deleted
            mock_azure_blob_service.delete_blob.assert_called_once()