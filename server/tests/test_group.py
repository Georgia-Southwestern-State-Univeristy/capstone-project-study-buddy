import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask
from bson import ObjectId
from routes.group import groups_routes
from pydantic import ValidationError
import io

# Import the groups_routes Blueprint

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(groups_routes)
    # Ensure all endpoints are properly registered including the /users/list
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestCreateGroup:
    @patch('routes.group.StudyGroup')
    @patch('routes.group.User')
    @patch('routes.group.MongoDBClient')
    def test_create_group_success(self, mock_mongodb, mock_user, mock_study_group, client):
        """Test successful group creation"""
        # Setup mocks
        mock_group_instance = MagicMock()
        mock_group_instance.created_by = "user123"
        mock_group_instance.admins = ["user123"]
        mock_group_instance.members = []
        mock_group_instance.name = "Test Group"
        mock_group_instance.dict.return_value = {
            "created_by": "user123",
            "admins": ["user123"],
            "members": [],
            "name": "Test Group",
            "description": "Test description",
            "privacy": "public"
        }
        
        mock_study_group.return_value = mock_group_instance
        
        # Mock user exists
        mock_user.find_by_id.return_value = {"_id": "user123", "name": "Test User"}
        
        # Mock DB operations
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = None  # No existing group
        
        # Test data
        group_data = {
            "created_by": "user123",
            "name": "Test Group",
            "description": "Test description",
            "privacy": "public"
        }
        
        # Make request
        response = client.post(
            '/groups/create',
            data=json.dumps(group_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data["message"] == "Group created successfully"
        assert "group" in response_data
        
        # Verify mocks were called correctly
        mock_user.find_by_id.assert_called_with("user123")
        mock_db.__getitem__.return_value.find_one.assert_called_once()
        mock_db.__getitem__.return_value.insert_one.assert_called_once()
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.User')
    @patch('routes.group.MongoDBClient')
    @patch('routes.group.AzureBlobService')
    def test_create_group_with_file_upload(self, mock_azure_blob, mock_mongodb, mock_user, mock_study_group, client):
        """Test successful group creation with file upload"""
        # Setup mocks
        mock_group_instance = MagicMock()
        mock_group_instance.created_by = "user123"
        mock_group_instance.admins = ["user123"]
        mock_group_instance.members = []
        mock_group_instance.name = "Test Group"
        mock_group_instance.dict.return_value = {
            "created_by": "user123",
            "admins": ["user123"],
            "members": [],
            "name": "Test Group",
            "description": "Test description",
            "privacy": "public",
            "image_url": "https://test-storage.blob.core.windows.net/group-images/test.jpg"
        }
        
        mock_study_group.return_value = mock_group_instance
        
        # Mock user exists
        mock_user.find_by_id.return_value = {"_id": "user123", "name": "Test User"}
        
        # Mock DB operations
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = None  # No existing group

        # Mock Azure Blob Service
        mock_blob_service = MagicMock()
        mock_blob_service.upload_file.return_value = "https://test-storage.blob.core.windows.net/group-images/test.jpg"
        mock_azure_blob.get_group_images_service.return_value = mock_blob_service
        
        # Prepare test data with file
        file_data = io.BytesIO(b"test file content")
        
        # Create form data
        data = dict(
            name="Test Group",
            description="Test description",
            privacy="public",
            created_by="user123",
            topics=json.dumps(["python", "study"]),
            rules=json.dumps(["Be respectful", "No spamming"]),
            members=json.dumps([])
        )
        
        # Make request with file
        response = client.post(
            '/groups/create',
            data=dict(
                data,
                group_image=(file_data, 'test.jpg')
            ),
            content_type='multipart/form-data'
        )
        
        # Assertions
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data["message"] == "Group created successfully"
        assert "group" in response_data
        
        # Verify file was uploaded
        mock_azure_blob.get_group_images_service.assert_called_once()
        mock_blob_service.upload_file.assert_called_once()
        
        # Verify DB operations
        mock_db.__getitem__.return_value.insert_one.assert_called_once()
    
    @patch('routes.group.StudyGroup')
    def test_create_group_validation_error(self, mock_study_group, client):
        """Test group creation with validation error"""
        # Setup mock to raise ValidationError properly
        error = ValidationError.from_exception_data(
            title="ValidationError",
            line_errors=[{
                'loc': ('name',),
                'msg': 'field required',
                'type': 'missing'  # Simplified error type
            }]
        )
        mock_study_group.side_effect = error
        
        # Test data (missing required field 'name')
        group_data = {
            "description": "Test description",
            "privacy": "public",
            "created_by": "user123"
        }
        
        # Make request
        response = client.post(
            '/groups/create',
            data=json.dumps(group_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Validation failed" in response_data["error"]
        assert "details" in response_data
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.User')
    def test_create_group_invalid_creator(self, mock_user, mock_study_group, client):
        """Test group creation with invalid creator ID"""
        # Setup mocks
        mock_group_instance = MagicMock()
        mock_group_instance.created_by = "invalid_user"
        mock_group_instance.admins = ["invalid_user"]
        mock_group_instance.members = []
        mock_study_group.return_value = mock_group_instance
        
        # Mock user does not exist
        mock_user.find_by_id.return_value = None
        
        # Test data
        group_data = {
            "created_by": "invalid_user",
            "name": "Test Group",
            "description": "Test description"
        }
        
        # Make request
        response = client.post(
            '/groups/create',
            data=json.dumps(group_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Creator user ID" in response_data["error"]
        
        # Verify mock was called
        mock_user.find_by_id.assert_called_with("invalid_user")
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.User')
    def test_create_group_invalid_admin(self, mock_user, mock_study_group, client):
        """Test group creation with invalid admin ID"""
        # Setup mocks
        mock_group_instance = MagicMock()
        mock_group_instance.created_by = "user123"
        mock_group_instance.admins = ["user123", "invalid_admin"]
        mock_group_instance.members = []
        mock_study_group.return_value = mock_group_instance
        
        # Mock creator exists but admin doesn't
        mock_user.find_by_id.side_effect = lambda user_id: {"_id": user_id, "name": "Test User"} if user_id == "user123" else None
        
        # Test data
        group_data = {
            "created_by": "user123",
            "admins": ["invalid_admin"],  # This will also include created_by
            "name": "Test Group"
        }
        
        # Make request
        response = client.post(
            '/groups/create',
            data=json.dumps(group_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Admin user ID" in response_data["error"]
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.User')
    def test_create_group_invalid_member(self, mock_user, mock_study_group, client):
        """Test group creation with invalid member ID"""
        # Setup mocks
        mock_group_instance = MagicMock()
        mock_group_instance.created_by = "user123"
        mock_group_instance.admins = ["user123"]
        mock_group_instance.members = ["invalid_member"]
        mock_study_group.return_value = mock_group_instance
        
        # Mock creator exists but member doesn't
        mock_user.find_by_id.side_effect = lambda user_id: {"_id": user_id, "name": "Test User"} if user_id == "user123" else None
        
        # Test data
        group_data = {
            "created_by": "user123",
            "members": ["invalid_member"],
            "name": "Test Group"
        }
        
        # Make request
        response = client.post(
            '/groups/create',
            data=json.dumps(group_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Member user ID" in response_data["error"]
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.User')
    @patch('routes.group.MongoDBClient')
    def test_create_group_duplicate_name(self, mock_mongodb, mock_user, mock_study_group, client):
        """Test group creation with duplicate name"""
        # Setup mocks
        mock_group_instance = MagicMock()
        mock_group_instance.created_by = "user123"
        mock_group_instance.admins = ["user123"]
        mock_group_instance.members = []
        mock_group_instance.name = "Existing Group"
        mock_study_group.return_value = mock_group_instance
        
        # Mock user exists
        mock_user.find_by_id.return_value = {"_id": "user123", "name": "Test User"}
        
        # Mock DB operations - group with same name exists
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = {"name": "Existing Group"}
        
        # Test data
        group_data = {
            "created_by": "user123",
            "name": "Existing Group",
            "description": "Test description"
        }
        
        # Make request
        response = client.post(
            '/groups/create',
            data=json.dumps(group_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "already exists" in response_data["error"]
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_create_group_server_error(self, mock_mongodb, mock_study_group, client):
        """Test group creation with server error"""
        # Setup mock to raise exception
        mock_mongodb.get_client.side_effect = Exception("Database connection error")
        
        # Test data
        group_data = {
            "name": "Test Group",
            "description": "Test description",
            "created_by": "user123"
        }
        
        # Make request
        response = client.post(
            '/groups/create',
            data=json.dumps(group_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Database connection error" in response_data["error"]


class TestJoinGroup:
    @patch('routes.group.User')
    @patch('routes.group.MongoDBClient')
    def test_join_group_success(self, mock_mongodb, mock_user, client):
        """Test successful group join"""
        # Setup mocks
        mock_user.find_by_id.return_value = {"_id": "user123", "name": "Test User"}
        
        # Mock DB operations
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = {
            "_id": "group456", 
            "name": "Test Group",
            "members": ["other_user"]
        }
        
        # Test data
        join_data = {
            "group_id": "group456",
            "user_id": "user123"
        }
        
        # Make request
        response = client.post(
            '/groups/join',
            data=json.dumps(join_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert "joined group" in response_data["message"]
        
        # Verify update was called
        mock_db.__getitem__.return_value.update_one.assert_called_once_with(
            {"_id": "group456"},
            {"$addToSet": {"members": "user123"}}
        )
    
    def test_join_group_missing_group_id(self, client):
        """Test join group with missing group_id"""
        # Test data
        join_data = {
            "user_id": "user123"
            # Missing group_id
        }
        
        # Make request
        response = client.post(
            '/groups/join',
            data=json.dumps(join_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "group_id is required" in response_data["error"]
    
    def test_join_group_missing_user_id(self, client):
        """Test join group with missing user_id"""
        # Test data
        join_data = {
            "group_id": "group456"
            # Missing user_id
        }
        
        # Make request
        response = client.post(
            '/groups/join',
            data=json.dumps(join_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "user_id is required" in response_data["error"]
    
    @patch('routes.group.User')
    def test_join_group_invalid_user(self, mock_user, client):
        """Test join group with invalid user_id"""
        # Setup mock
        mock_user.find_by_id.return_value = None
        
        # Test data
        join_data = {
            "group_id": "group456",
            "user_id": "invalid_user"
        }
        
        # Make request
        response = client.post(
            '/groups/join',
            data=json.dumps(join_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "does not exist" in response_data["error"]
    
    @patch('routes.group.User')
    @patch('routes.group.MongoDBClient')
    def test_join_group_invalid_group(self, mock_mongodb, mock_user, client):
        """Test join group with invalid group_id"""
        # Setup mocks
        mock_user.find_by_id.return_value = {"_id": "user123", "name": "Test User"}
        
        # Mock DB operations - group doesn't exist
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = None
        
        # Test data
        join_data = {
            "group_id": "invalid_group",
            "user_id": "user123"
        }
        
        # Make request
        response = client.post(
            '/groups/join',
            data=json.dumps(join_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "does not exist" in response_data["error"]
    
    @patch('routes.group.User')
    @patch('routes.group.MongoDBClient')
    def test_join_group_already_member(self, mock_mongodb, mock_user, client):
        """Test join group when user is already a member"""
        # Setup mocks
        mock_user.find_by_id.return_value = {"_id": "user123", "name": "Test User"}
        
        # Mock DB operations
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value.find_one.return_value = {
            "_id": "group456", 
            "name": "Test Group",
            "members": ["user123"]  # User already in members
        }
        
        # Test data
        join_data = {
            "group_id": "group456",
            "user_id": "user123"
        }
        
        # Make request
        response = client.post(
            '/groups/join',
            data=json.dumps(join_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert "already a member" in response_data["message"]
        
        # Verify update was not called
        mock_db.__getitem__.return_value.update_one.assert_not_called()
    
    @patch('routes.group.User')
    @patch('routes.group.MongoDBClient')
    def test_join_group_server_error(self, mock_mongodb, mock_user, client):
        """Test join group with server error"""
        # Setup mocks
        mock_user.find_by_id.return_value = {"_id": "user123", "name": "Test User"}
        mock_mongodb.get_client.side_effect = Exception("Database error during join operation")
        
        # Test data
        join_data = {
            "group_id": "group456",
            "user_id": "user123"
        }
        
        # Make request
        response = client.post(
            '/groups/join',
            data=json.dumps(join_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Database error during join operation" in response_data["error"]


class TestRetrieveGroups:
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_no_filters(self, mock_mongodb, mock_study_group, client):
        """Test retrieving groups with no filters"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock group instances
        group1 = MagicMock()
        group1.dict.return_value = {"name": "Group 1"}
        group2 = MagicMock()
        group2.dict.return_value = {"name": "Group 2"}
        
        # Mock the parsing
        mock_study_group.parse_obj.side_effect = [group1, group2]
        
        # Mock find operation
        mock_groups = [{"name": "Group 1"}, {"name": "Group 2"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_groups
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents.return_value = 2
        
        # Make request
        response = client.get('/groups/retrieve')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert "Groups retrieved successfully" == response_data["message"]
        assert "data" in response_data
        assert len(response_data["data"]) == 2
        assert "pagination" in response_data
        assert response_data["pagination"]["total"] == 2
        
        # Verify mocks were called correctly
        mock_db.__getitem__.return_value.find.assert_called_once_with({})
        mock_cursor.skip.assert_called_once_with(0)
        mock_cursor.skip.return_value.limit.assert_called_once_with(10)
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_with_privacy_filter(self, mock_mongodb, mock_study_group, client):
        """Test retrieving groups with privacy filter"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock group instance
        group = MagicMock()
        group.dict.return_value = {"name": "Private Group", "privacy": "private"}
        
        # Mock the parsing
        mock_study_group.parse_obj.return_value = group
        
        # Mock find operation
        mock_groups = [{"name": "Private Group", "privacy": "private"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_groups
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents.return_value = 1
        
        # Make request
        response = client.get('/groups/retrieve?privacy=private')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert response_data["data"][0]["privacy"] == "private"
        
        # Verify mocks were called correctly
        mock_db.__getitem__.return_value.find.assert_called_once_with({"privacy": "private"})
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_with_name_filter(self, mock_mongodb, mock_study_group, client):
        """Test retrieving groups with name filter"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock group instance
        group = MagicMock()
        group.dict.return_value = {"name": "Math Study Group"}
        
        # Mock the parsing
        mock_study_group.parse_obj.return_value = group
        
        # Mock find operation
        mock_groups = [{"name": "Math Study Group"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_groups
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents.return_value = 1
        
        # Make request
        response = client.get('/groups/retrieve?name=Math')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert "Math" in response_data["data"][0]["name"]
        
        # Verify mocks were called correctly
        mock_db.__getitem__.return_value.find.assert_called_once_with({"name": {"$regex": "Math", "$options": "i"}})
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_with_topic_filter(self, mock_mongodb, mock_study_group, client):
        """Test retrieving groups with topic filter"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock group instance
        group = MagicMock()
        group.dict.return_value = {"name": "Physics Group", "topics": ["physics", "science"]}
        
        # Mock the parsing
        mock_study_group.parse_obj.return_value = group
        
        # Mock find operation
        mock_groups = [{"name": "Physics Group", "topics": ["physics", "science"]}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_groups
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents.return_value = 1
        
        # Make request
        response = client.get('/groups/retrieve?topic=physics')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert "physics" in response_data["data"][0]["topics"]
        
        # Verify mocks were called correctly
        mock_db.__getitem__.return_value.find.assert_called_once_with({"topics": {"$in": ["physics"]}})
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_with_pagination(self, mock_mongodb, mock_study_group, client):
        """Test retrieving groups with pagination"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock group instance
        group = MagicMock()
        group.dict.return_value = {"name": "Group on page 2"}
        
        # Mock the parsing
        mock_study_group.parse_obj.return_value = group
        
        # Mock find operation
        mock_groups = [{"name": "Group on page 2"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_groups
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents.return_value = 15
        
        # Make request for page 2 with limit 5
        response = client.get('/groups/retrieve?page=2&limit=5')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert "pagination" in response_data
        assert response_data["pagination"]["page"] == 2
        assert response_data["pagination"]["limit"] == 5
        assert response_data["pagination"]["total"] == 15
        
        # Verify mocks were called correctly
        mock_cursor.skip.assert_called_once_with(5)
        mock_cursor.skip.return_value.limit.assert_called_once_with(5)
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_with_combined_filters(self, mock_mongodb, mock_study_group, client):
        """Test retrieving groups with multiple filters"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock group instance
        group = MagicMock()
        group.dict.return_value = {"name": "Math Study", "privacy": "public", "topics": ["mathematics"]}
        
        # Mock the parsing
        mock_study_group.parse_obj.return_value = group
        
        # Mock find operation
        mock_groups = [{"name": "Math Study", "privacy": "public", "topics": ["mathematics"]}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_groups
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents.return_value = 1
        
        # Make request with multiple filters
        response = client.get('/groups/retrieve?privacy=public&name=Math&topic=mathematics')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert response_data["data"][0]["privacy"] == "public"
        assert "Math" in response_data["data"][0]["name"]
        assert "mathematics" in response_data["data"][0]["topics"]
        
        # Verify expected query
        expected_query = {
            "privacy": "public",
            "name": {"$regex": "Math", "$options": "i"},
            "topics": {"$in": ["mathematics"]}
        }
        mock_db.__getitem__.return_value.find.assert_called_once_with(expected_query)
    
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_exception(self, mock_mongodb, client):
        """Test retrieving groups when an exception occurs"""
        # Setup mock to raise exception
        mock_mongodb.get_client.side_effect = Exception("Test database error")
        
        # Make request
        response = client.get('/groups/retrieve')
        
        # Assertions
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Test database error" in response_data["error"]
    
    @patch('routes.group.StudyGroup')
    @patch('routes.group.MongoDBClient')
    def test_retrieve_groups_empty_result(self, mock_mongodb, mock_study_group, client):
        """Test retrieving groups with no matching results"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock empty result
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = []
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_db.__getitem__.return_value.count_documents.return_value = 0
        
        # Make request
        response = client.get('/groups/retrieve?name=NonExistentGroup')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert len(response_data["data"]) == 0
        assert response_data["pagination"]["total"] == 0


class TestListUsers:
    @patch('routes.group.MongoDBClient')
    def test_list_users_success(self, mock_mongodb, client):
        """Test successful users list retrieval"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock users data with proper MongoDB cursor simulation
        mock_users = [
            {"_id": "user1", "username": "testuser1", "name": "Test User 1", "profile_picture": "url1"},
            {"_id": "user2", "username": "testuser2", "name": "Test User 2", "profile_picture": "url2"}
        ]
        
        # Better cursor simulation that allows MongoDB-style iteration
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter(mock_users)
        mock_cursor.limit.return_value = mock_cursor  # For chained limit() call
        
        # Setup mock to return the cursor
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        
        # Make request
        response = client.get('/users/list')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert "Users retrieved successfully" == response_data["message"]
        assert "data" in response_data
        assert len(response_data["data"]) == 2
        
        # Check user data
        assert response_data["data"][0]["username"] == "testuser1"
        assert response_data["data"][1]["username"] == "testuser2"
        
        # Verify find was called with correct projection
        mock_db.__getitem__.return_value.find.assert_called_once_with(
            {}, 
            {"_id": 1, "username": 1, "name": 1, "profile_picture": 1}
        )
    
    @patch('routes.group.MongoDBClient')
    def test_list_users_with_search(self, mock_mongodb, client):
        """Test users list retrieval with search parameter"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock users data with proper MongoDB cursor simulation
        mock_users = [
            {"_id": "user1", "username": "alice", "name": "Alice Smith", "profile_picture": "url1"},
        ]
        
        # Better cursor simulation that allows MongoDB-style iteration
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter(mock_users)
        mock_cursor.limit.return_value = mock_cursor  # For chained limit() call
        
        # Setup mock to return the cursor
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        
        # Make request with search parameter
        response = client.get('/users/list?search=alice')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert response_data["data"][0]["username"] == "alice"
        
        # Verify find was called with correct query and projection
        mock_db.__getitem__.return_value.find.assert_called_once_with(
            {"username": {"$regex": "alice", "$options": "i"}}, 
            {"_id": 1, "username": 1, "name": 1, "profile_picture": 1}
        )
    
    @patch('routes.group.MongoDBClient')
    def test_list_users_empty_result(self, mock_mongodb, client):
        """Test users list retrieval with no matching results"""
        # Setup mocks
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock empty result with proper MongoDB cursor simulation
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter([])
        mock_cursor.limit.return_value = mock_cursor  # For chained limit() call
        
        # Setup mock to return the cursor
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        
        # Make request with non-matching search
        response = client.get('/users/list?search=nonexistentuser')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "data" in response_data
        assert len(response_data["data"]) == 0
    
    @patch('routes.group.MongoDBClient')
    def test_list_users_server_error(self, mock_mongodb, client):
        """Test users list retrieval with server error"""
        # Setup mock to raise exception
        mock_mongodb.get_client.side_effect = Exception("Database connection error")
        
        # Make request
        response = client.get('/users/list')
        
        # Assertions
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Database connection error" in response_data["error"]