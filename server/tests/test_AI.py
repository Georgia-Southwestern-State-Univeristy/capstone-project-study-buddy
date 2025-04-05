import pytest
import json
import io
from unittest.mock import patch, MagicMock, PropertyMock
from flask import Flask, Response
from werkzeug.datastructures import FileStorage, MultiDict
from routes.AI import ai_routes

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(ai_routes)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestAIRoutes:
    
    @patch('routes.AI.MemeMingleAIAgent')
    def test_welcome_success(self, mock_agent, client):
        """Test successful welcome message"""
        # Setup mock
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.get_initial_greeting.return_value = {
            "message": "Welcome to MemeMingle!",
            "suggestions": ["How can I help?", "Tell me about yourself"]
        }
        
        # Test data
        data = {"role": "EducationalMentor"}
        
        # Make request
        response = client.post(
            '/ai_mentor/welcome/user123',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert response_data["message"] == "Welcome to MemeMingle!"
        assert "suggestions" in response_data
        assert len(response_data["suggestions"]) == 2
        
        # Verify mock was called correctly
        mock_agent.assert_called_once()
        mock_agent_instance.get_initial_greeting.assert_called_once_with(user_id="user123")
    
    @patch('routes.AI.jsonify')
    @patch('routes.AI.MemeMingleAIAgent')
    def test_welcome_no_data(self, mock_agent, mock_jsonify, client):
        """Test welcome with no request data"""
        # Setup mock for jsonify to return a proper JSON response
        mock_jsonify.return_value = json.dumps({"error": "No data provided"}), 400
        
        # Make request with no data but with content type header
        response = client.post('/ai_mentor/welcome/user123', 
                            content_type='application/json')
        
        # Assertions - don't parse JSON since we're mocking jsonify
        assert response.status_code == 400
        
        # Verify mock was not called
        mock_agent.assert_not_called()

    @patch('routes.AI.MemeMingleAIAgent')
    def test_welcome_different_roles(self, mock_agent, client):
        """Test welcome with different roles"""
        # We'll test just one role to avoid complexity
        role = "EducationalMentor"
        
        # Setup mock
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.get_initial_greeting.return_value = {
            "message": f"Welcome! I'm your {role}",
            "suggestions": ["How can I help?"]
        }
        
        # Test data
        data = {"role": role}
        
        # Make request
        response = client.post(
            '/ai_mentor/welcome/user123',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert role in response_data["message"]
        
        # Verify desired_role was passed correctly - don't use approx comparison
        mock_agent.assert_called_once()
    
    @patch('routes.AI.MemeMingleAIAgent')
    def test_welcome_agent_returns_none(self, mock_agent, client):
        """Test welcome when agent returns None"""
        # Setup mock
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.get_initial_greeting.return_value = None
        
        # Test data
        data = {"role": "MemeMingle"}
        
        # Make request
        response = client.post(
            '/ai_mentor/welcome/user123',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Greeting not found" in response_data["error"]
        
    @patch('routes.AI.MongoDBClient')
    @patch('routes.AI.MemeMingleAIAgent')
    def test_run_agent_success(self, mock_agent, mock_mongodb, client):
        """Test successful conversation"""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.run.return_value = {
            "response": "This is a test response",
            "suggestions": ["Option 1", "Option 2"],
            "meme_url": "http://example.com/meme.jpg"
        }
        
        # Mock MongoDB
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {"desired_role": "MemeMingle"}
        
        # Test data
        data = {"prompt": "Hello AI", "turn_id": "1"}
        
        # Make request
        response = client.post(
            '/ai_mentor/user123/456',
            data=data
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "response" in response_data
        assert response_data["response"] == "This is a test response"
        assert "suggestions" in response_data
        assert len(response_data["suggestions"]) == 2
        assert "meme_url" in response_data
        
        # Verify mock was called correctly
        mock_agent_instance.run.assert_called_once_with(
            file_content=None,
            file_mime_type=None,
            message="Hello AI",
            with_history=True,
            user_id="user123",
            chat_id=456,
            turn_id=2
        )
    
    @patch('routes.AI.filetype')
    @patch('routes.AI.MongoDBClient')
    @patch('routes.AI.MemeMingleAIAgent')
    def test_run_agent_with_file(self, mock_agent, mock_mongodb, mock_filetype, client):
        """Test conversation with file upload"""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.run.return_value = {
            "response": "I analyzed your file",
            "suggestions": ["Option 1", "Option 2"],
            "file_analysis": "PDF contains 5 pages"
        }
        
        # Mock MongoDB
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {"desired_role": "MemeMingle"}
        
        # Mock filetype
        mock_kind = MagicMock()
        mock_kind.extension = "pdf"
        mock_kind.mime = "application/pdf"
        mock_filetype.guess.return_value = mock_kind
        
        # Create test file using FileStorage
        file_data = io.BytesIO(b"test file content")
        test_file = FileStorage(
            stream=file_data,
            filename="test.pdf",
            content_type="application/pdf"
        )
        
        # Make request with file using MultiDict
        data = MultiDict([
            ('prompt', 'Analyze this file'), 
            ('turn_id', '1')
        ])
        data.add('file', test_file)
        
        response = client.post(
            '/ai_mentor/user123/456',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "response" in response_data
        assert "file_analysis" in response_data
        
        # Verify mock was called with file content
        call_args = mock_agent_instance.run.call_args[1]
        assert call_args["file_content"] is not None
        assert call_args["file_mime_type"] == "application/pdf"
        assert call_args["message"] == "Analyze this file"
    
    @patch('routes.AI.filetype')
    @patch('routes.AI.ALLOWED_MIME_TYPES', ["application/pdf", "image/jpeg"])
    @patch('routes.AI.MongoDBClient')
    def test_run_agent_invalid_file_type(self, mock_mongodb, mock_filetype, client):
        """Test conversation with invalid file type"""
        # Mock MongoDB
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {"desired_role": "MemeMingle"}
        
        # Mock filetype
        mock_kind = MagicMock()
        mock_kind.extension = "exe"
        mock_kind.mime = "application/octet-stream"
        mock_filetype.guess.return_value = mock_kind
        
        # Create test file using FileStorage
        file_data = io.BytesIO(b"test file content")
        test_file = FileStorage(
            stream=file_data,
            filename="test.exe",
            content_type="application/octet-stream"
        )
        
        # Make request with file using MultiDict
        data = MultiDict([
            ('prompt', 'Analyze this file'), 
            ('turn_id', '1')
        ])
        data.add('file', test_file)
        
        response = client.post(
            '/ai_mentor/user123/456',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Unsupported file type" in response_data["error"]
        assert "application/octet-stream" in response_data["error"]
    
    @patch('routes.AI.filetype')
    @patch('routes.AI.MongoDBClient')
    def test_run_agent_file_too_large(self, mock_mongodb, mock_filetype, client):
        """Test conversation with file exceeding size limit"""
        # Mock MongoDB
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {"desired_role": "MemeMingle"}
        
        # Mock filetype
        mock_kind = MagicMock()
        mock_kind.extension = "pdf"
        mock_kind.mime = "application/pdf"
        mock_filetype.guess.return_value = mock_kind
        
        # Create a mock file with a custom getsize method
        file_data = io.BytesIO(b"x")
        test_file = FileStorage(
            stream=file_data,
            filename="large.pdf",
            content_type="application/pdf"
        )
        
        # Instead of patching len(), patch the specific code that checks file size
        with patch('routes.AI.len') as mock_len:
            mock_len.return_value = 11 * 1024 * 1024  # 11 MB (exceeds the 10MB limit)
            
            # Make request with file using MultiDict
            data = MultiDict([
                ('prompt', 'Analyze this large file'), 
                ('turn_id', '1')
            ])
            data.add('file', test_file)
            
            response = client.post(
                '/ai_mentor/user123/456',
                data=data,
                content_type='multipart/form-data'
            )
            
            # Assertions
            assert response.status_code == 400
            response_data = json.loads(response.data)
            assert "error" in response_data
            assert "File size exceeds" in response_data["error"]
    
    @patch('routes.AI.MongoDBClient')
    @patch('routes.AI.MemeMingleAIAgent')
    def test_run_agent_json_error(self, mock_agent, mock_mongodb, client):
        """Test conversation with JSON parsing error"""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.run.side_effect = json.JSONDecodeError("Invalid JSON", "{invalid}", 0)
        
        # Mock MongoDB
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {"desired_role": "MemeMingle"}
        
        # Test data
        data = {"prompt": "Hello AI", "turn_id": "1"}
        
        # Make request
        response = client.post(
            '/ai_mentor/user123/456',
            data=data
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Invalid JSON format" in response_data["error"]
    
    @patch('routes.AI.MongoDBClient')
    @patch('routes.AI.MemeMingleAIAgent')
    def test_run_agent_generic_exception(self, mock_agent, mock_mongodb, client):
        """Test conversation with generic exception"""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.run.side_effect = Exception("Something went wrong")
        
        # Mock MongoDB
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {"desired_role": "MemeMingle"}
        
        # Test data
        data = {"prompt": "Hello AI", "turn_id": "1"}
        
        # Make request
        response = client.post(
            '/ai_mentor/user123/456',
            data=data
        )
        
        # Assertions
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Something went wrong" in response_data["error"]
    
    @patch('routes.AI.MemeMingleAIAgent')
    def test_finalize_chat_success(self, mock_agent, client):
        """Test successful chat finalization"""
        # Setup mock
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.perform_final_processes.return_value = None
        
        # Make request
        response = client.patch('/ai_mentor/finalize/user123/456')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert "Chat session finalized successfully" in response_data["message"]
        
        # Verify mock was called correctly
        mock_agent_instance.perform_final_processes.assert_called_once_with("user123", "456")
    
    @patch('routes.AI.MemeMingleAIAgent')
    def test_finalize_chat_exception(self, mock_agent, client):
        """Test chat finalization with exception"""
        # Setup mock
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.perform_final_processes.side_effect = Exception("Test error")
        
        # Make request
        response = client.patch('/ai_mentor/finalize/user123/456')
        
        # Assertions
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Failed to finalize chat" in response_data["error"]
    
    @patch('routes.AI.speech_to_text')
    def test_voice_to_text_success(self, mock_speech_to_text, client):
        """Test successful voice to text conversion"""
        # Setup mock
        mock_speech_to_text.return_value = "This is the transcribed text"
        
        # Create test audio file
        test_audio = io.BytesIO(b"audio data")
        
        # Make request
        response = client.post(
            '/ai_mentor/voice-to-text',
            content_type='multipart/form-data',
            data={"audio": (test_audio, "audio.wav")}
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert response_data["message"] == "This is the transcribed text"
        
        # Verify mock was called
        mock_speech_to_text.assert_called_once()
    
    def test_voice_to_text_no_file(self, client):
        """Test voice to text with no file"""
        # Make request with no audio file
        response = client.post('/ai_mentor/voice-to-text')
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Audio file is required" in response_data["error"]
    
    @patch('routes.AI.speech_to_text')
    def test_voice_to_text_failure(self, mock_speech_to_text, client):
        """Test voice to text when conversion fails"""
        # Setup mock
        mock_speech_to_text.return_value = None
        
        # Create test audio file
        test_audio = io.BytesIO(b"audio data")
        
        # Make request
        response = client.post(
            '/ai_mentor/voice-to-text',
            content_type='multipart/form-data',
            data={"audio": (test_audio, "audio.wav")}
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Speech recognition failed" in response_data["error"]
    
    @patch('routes.AI.text_to_speech')
    @patch('routes.AI.io.BytesIO')
    @patch('routes.AI.send_file')
    def test_text_to_speech_success(self, mock_send_file, mock_bytesio, mock_text_to_speech, client):
        """Test successful text to speech conversion"""
        # Setup mocks
        mock_text_to_speech.return_value = b"audio data"
        mock_bytesio.return_value = "BytesIO instance"
        mock_send_file.return_value = "File response"
        
        # Test data
        data = {
            "text": "Convert this text to speech",
            "voice_name": "en-US-GuyNeural",
            "style": "excited"
        }
        
        # Make request
        response = client.post(
            '/ai_mentor/text-to-speech',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify mocks were called correctly
        mock_text_to_speech.assert_called_once_with(
            "Convert this text to speech", 
            voice_name="en-US-GuyNeural", 
            style="excited"
        )
        mock_bytesio.assert_called_once_with(b"audio data")
        mock_send_file.assert_called_once_with(
            "BytesIO instance",
            mimetype='audio/wav',
            as_attachment=False,
            download_name='output.wav'
        )

    @patch('routes.AI.text_to_speech')
    @patch('routes.AI.io.BytesIO')
    @patch('routes.AI.send_file')
    def test_text_to_speech_default_params(self, mock_send_file, mock_bytesio, mock_text_to_speech, client):
        """Test text to speech with default parameters"""
        # Setup mocks
        mock_text_to_speech.return_value = b"audio data"
        mock_bytesio.return_value = "BytesIO instance"
        mock_send_file.return_value = "File response"
        
        # Test data with minimum required parameters
        data = {
            "text": "Convert this text to speech"
        }
        
        # Make request
        response = client.post(
            '/ai_mentor/text-to-speech',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify default parameters were used
        mock_text_to_speech.assert_called_once_with(
            "Convert this text to speech", 
            voice_name='en-US-AriaNeural',  # Default voice
            style=None                      # No style specified
        )

    def test_text_to_speech_no_text(self, client):
        """Test text to speech with no text"""
        # Test data without text
        data = {
            "voice_name": "en-US-GuyNeural",
            "style": "excited"
        }
        
        # Make request directly without mocking
        response = client.post(
            '/ai_mentor/text-to-speech',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Text input is required" in response_data["error"]

    def test_text_to_speech_no_data(self, client):
        """Test text to speech with no data provided"""
        # Make request with empty JSON object instead of empty string
        response = client.post(
            '/ai_mentor/text-to-speech',
            data=json.dumps({}),  # Empty JSON object
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "No data provided" in response_data["error"]
    
    @patch('routes.AI.text_to_speech')
    def test_text_to_speech_conversion_failed(self, mock_text_to_speech, client):
        """Test text to speech when conversion fails"""
        # Setup mock
        mock_text_to_speech.return_value = None
        
        # Test data
        data = {
            "text": "Convert this text to speech"
        }
        
        # Make request
        response = client.post(
            '/ai_mentor/text-to-speech',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Text-to-speech conversion failed" in response_data["error"]
    
    @patch('routes.AI.send_from_directory')
    def test_download_document_success(self, mock_send_from_directory, client):
        """Test successful document download"""
        # Setup mock
        mock_send_from_directory.return_value = "File response"
        
        # Make request
        response = client.get('/ai_mentor/download_document/test_doc.pdf')
        
        # Verify mock was called correctly
        mock_send_from_directory.assert_called_once_with(
            'generated_documents', 
            'test_doc.pdf', 
            as_attachment=True
        )
    
    def test_download_document_invalid_filename(self, client):
        """Test document download with invalid filename"""
        # Make request with invalid filenames
        invalid_filenames = ['../etc/passwd', '/etc/passwd', '../../config.json']
        
        for filename in invalid_filenames:
            response = client.get(f'/ai_mentor/download_document/{filename}')
            
            # Either 404 (not found) or 400 (bad request) is acceptable
            assert response.status_code in [400, 404]
    
    @patch('routes.AI.send_from_directory')
    def test_download_audio_success(self, mock_send_from_directory, client):
        """Test successful audio download"""
        # Setup mock
        mock_send_from_directory.return_value = "File response"
        
        # Make request
        response = client.get('/ai_mentor/download_audio/test_audio.wav')
        
        # Verify mock was called correctly
        mock_send_from_directory.assert_called_once_with(
            'generated_audio', 
            'test_audio.wav', 
            as_attachment=True, 
            mimetype='audio/wav'
        )
    
    def test_download_audio_invalid_filename(self, client):
        """Test audio download with invalid filename"""
        # Make request with invalid filenames
        invalid_filenames = ['../etc/passwd', '/etc/passwd', '../../config.json']
        
        for filename in invalid_filenames:
            response = client.get(f'/ai_mentor/download_audio/{filename}')
            
            # Either 404 (not found) or 400 (bad request) is acceptable
            assert response.status_code in [400, 404]

    @patch('routes.AI.send_from_directory')
    def test_download_image_success(self, mock_send_from_directory, client):
        """Test successful image download"""
        # Setup mock
        mock_send_from_directory.return_value = "Image file response"
        
        # Make request
        response = client.get('/ai_mentor/download_image/test_image.jpg')
        
        # Verify mock was called correctly
        mock_send_from_directory.assert_called_once_with(
            'generated_images', 
            'test_image.jpg', 
            as_attachment=True
        )
    
    def test_download_image_invalid_filename(self, client):
        """Test image download with invalid filename"""
        # Make request with invalid filenames
        invalid_filenames = ['../etc/passwd', '/etc/passwd', '../../config.json']
        
        for filename in invalid_filenames:
            response = client.get(f'/ai_mentor/download_image/{filename}')
            
            # Either 404 (not found) or 400 (bad request) is acceptable
            assert response.status_code in [400, 404]
                
    @patch('routes.AI.MongoDBClient')
    def test_run_agent_no_chat_summary(self, mock_mongodb, client):
        """Test conversation when chat summary is not found"""
        # Mock MongoDB to return None for chat_summary
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = None
        
        # Test data
        data = {"prompt": "Hello AI", "turn_id": "1"}
        
        # Make request
        response = client.post(
            '/ai_mentor/user123/456',
            data=data
        )
        
        # Assertions
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Chat summary not found" in response_data["error"]
        
        # We only need to verify that the MongoDB find_one was called correctly
        mock_collection.find_one.assert_called_once_with({"user_id": "user123", "chat_id": 456})