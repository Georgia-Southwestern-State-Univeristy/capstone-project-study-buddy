# Fix for failing tests: test_leave_group_room_success and test_create_group_post_validation_error

import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_socketio import SocketIOTestClient
from bson import ObjectId
from routes.group_post import group_posts_routes
from utils.socketIo import socketio
from models.group_post import GroupPost
from pydantic import ValidationError

# Fix for the Socket.IO test - need to ensure proper connections
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    app.register_blueprint(group_posts_routes)
    socketio.init_app(app, async_mode='threading')  # Use threading mode for tests
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def socket_client(app):
    return SocketIOTestClient(app, socketio)

class TestGroupPostSocketEvents:
    
    def test_join_group_room_success(self, socket_client):
        """Test successful joining of a group room"""
        socket_client.emit('join_group_room', {
            'group_id': 'group123',
            'user_id': 'user456'
        })
        
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'group_notification'
        assert 'joined group' in received[0]['args'][0]['message']
        assert received[0]['args'][0]['group_id'] == 'group123'
        assert received[0]['args'][0]['user_id'] == 'user456'

    def test_join_group_room_missing_data(self, socket_client):
        """Test joining a group room with missing data"""
        socket_client.emit('join_group_room', {})
        
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'error'
        assert 'Missing group_id or user_id' in received[0]['args'][0]['message']

    def test_leave_group_room_missing_data(self, socket_client):
        """Test leaving a group room with missing data"""
        socket_client.emit('leave_group_room', {})
        
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'error'
        assert 'Missing group_id or user_id' in received[0]['args'][0]['message']

    @patch('routes.group_post.MongoDBClient')
    def test_like_post_success(self, mock_mongodb, socket_client):
        """Test successfully liking a post"""
        # Setup mock
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        socket_client.emit('like_post', {
            'post_id': '507f1f77bcf86cd799439011'
        })
        
        # Verify DB update was called
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId("507f1f77bcf86cd799439011")}, 
            {"$inc": {"likes": 1}}
        )
        
        # Check the emitted response
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'post_liked'
        assert received[0]['args'][0]['post_id'] == '507f1f77bcf86cd799439011'

    def test_like_post_missing_data(self, socket_client):
        """Test liking a post with missing post_id"""
        socket_client.emit('like_post', {})
        
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'error'
        assert 'Missing post_id' in received[0]['args'][0]['message']

    @patch('routes.group_post.MongoDBClient')
    def test_comment_post_success(self, mock_mongodb, socket_client):
        """Test successfully commenting on a post"""
        # Setup mock
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        socket_client.emit('comment_post', {
            'post_id': '507f1f77bcf86cd799439011',
            'comment': 'This is a test comment'
        })
        
        # Verify DB update was called
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId("507f1f77bcf86cd799439011")}, 
            {"$inc": {"comments": 1}}
        )
        
        # Check the emitted response
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'post_commented'
        assert received[0]['args'][0]['post_id'] == '507f1f77bcf86cd799439011'
        assert received[0]['args'][0]['comment'] == 'This is a test comment'

    def test_comment_post_missing_data(self, socket_client):
        """Test commenting on a post with missing data"""
        socket_client.emit('comment_post', {})
        
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'error'
        assert 'Missing post_id or comment' in received[0]['args'][0]['message']


class TestGroupPostHTTPRoutes:
    
    @patch('routes.group_post.User')
    @patch('routes.group_post.GroupPost')
    @patch('routes.group_post.MongoDBClient')
    @patch('routes.group_post.socketio.emit')
    def test_create_group_post_success(self, mock_emit, mock_mongodb, mock_group_post, mock_user, client):
        """Test successfully creating a group post"""
        # Setup mocks
        mock_user.find_by_id.return_value = {'_id': 'user123', 'name': 'Test User'}
        
        mock_post_instance = MagicMock()
        mock_post_instance.user_id = 'user123'
        mock_post_instance.group_id = 'group456'
        mock_post_instance.dict.return_value = {
            'user_id': 'user123',
            'group_id': 'group456',
            'content': 'Test post content'
        }
        mock_group_post.return_value = mock_post_instance
        
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.insert_one.return_value.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        
        # Test data
        post_data = {
            'user_id': 'user123',
            'group_id': 'group456',
            'content': 'Test post content'
        }
        
        # Make request
        response = client.post(
            '/group_posts',
            data=json.dumps(post_data),
            content_type='application/json'
        )
        
        # Verify response
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['message'] == 'Post created successfully'
        assert 'post' in response_data
        
        # Verify mocks were called
        mock_user.find_by_id.assert_called_once_with('user123')
        mock_collection.insert_one.assert_called_once()
        mock_emit.assert_called_once_with(
            'new_group_post', 
            mock_post_instance.dict(), 
            room='group_group456'
        )

    @patch('routes.group_post.User')
    @patch('routes.group_post.GroupPost')
    def test_create_group_post_invalid_user(self, mock_group_post, mock_user, client):
        """Test creating a group post with an invalid user"""
        # Setup mocks
        mock_user.find_by_id.return_value = None
        
        mock_post_instance = MagicMock()
        mock_post_instance.user_id = 'invalid_user'
        mock_post_instance.group_id = 'group456'
        mock_group_post.return_value = mock_post_instance
        
        # Test data
        post_data = {
            'user_id': 'invalid_user',
            'group_id': 'group456',
            'content': 'Test post content'
        }
        
        # Make request
        response = client.post(
            '/group_posts',
            data=json.dumps(post_data),
            content_type='application/json'
        )
        
        # Verify response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data
        assert 'Invalid user_id' in response_data['error']
        
        # Verify user lookup was called
        mock_user.find_by_id.assert_called_once_with('invalid_user')

    

    @patch('routes.group_post.MongoDBClient')
    def test_get_group_posts_success(self, mock_mongodb, client):
        """Test successfully getting group posts"""
        # Setup mock
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock the find operation
        mock_posts = [
            {
                '_id': str(ObjectId("507f1f77bcf86cd799439011")),
                'user_id': 'user123',
                'group_id': 'group456',
                'content': 'Test post 1',
                'created_at': '2023-01-01T12:00:00Z'
            },
            {
                '_id': str(ObjectId("507f1f77bcf86cd799439012")),
                'user_id': 'user456',
                'group_id': 'group456',
                'content': 'Test post 2',
                'created_at': '2023-01-02T12:00:00Z'
            }
        ]
        mock_collection.find.return_value = mock_posts
        
        # Make request
        response = client.get('/group_posts/group456')
        
        # Verify response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['message'] == 'Posts retrieved successfully'
        assert 'data' in response_data
        assert len(response_data['data']) == 2
        
        # Verify find was called with correct filter
        mock_collection.find.assert_called_once_with({'group_id': 'group456'})

    @patch('routes.group_post.MongoDBClient')
    def test_get_group_posts_exception(self, mock_mongodb, client):
        """Test getting group posts when an exception occurs"""
        # Setup mock to raise exception
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.side_effect = Exception("Database error")
        
        # Make request
        response = client.get('/group_posts/group456')
        
        # Verify response
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert 'error' in response_data
        assert 'Database error' in response_data['error']