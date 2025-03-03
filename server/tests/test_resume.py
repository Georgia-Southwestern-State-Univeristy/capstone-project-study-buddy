# Import the missing logging module
import pytest
import json
import logging
from unittest.mock import patch, MagicMock
from flask import Flask
from bson import ObjectId
from routes.resume import resume_routes
from models.resume import Resume, SocialAccount, EducationItem, ExperienceItem, ProjectItem, ReferenceItem
from pydantic import ValidationError

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(resume_routes)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_resume_data():
    return {
        "user_id": "user123",
        "fName": "John",
        "lName": "Doe",
        "description": "Software Engineer with 5+ years of experience",
        "career": "Software Engineering",
        "email": "john.doe@example.com",
        "phoneNum": "555-123-4567",
        "website": "https://johndoe.com",
        "socialAccounts": [
            {"platform": "LinkedIn", "handle": "@johndoe", "link": "https://linkedin.com/in/johndoe"}
        ],
        "skills": "Python, JavaScript, Docker, AWS",
        "education": [
            {"school": "University of Technology", "grad": "2020-05", "major": "Computer Science"}
        ],
        "experience": [
            {"exp_company": "Tech Inc.", "exp_date": "2020-2023", "exp_description": "Developed web applications"}
        ],
        "projects": [
            {"projectName": "Portfolio Website", "projectUrl": "https://github.com/johndoe/portfolio", "projectDesc": "Personal portfolio website"}
        ],
        "references": [
            {"refName": "Jane Smith", "refContact": "jane.smith@example.com"}
        ]
    }


class TestCreateResume:
    
    @patch('routes.resume.Resume')
    def test_create_resume_success(self, mock_resume, client, sample_resume_data):
        """Test successful resume creation"""
        # Setup mock
        mock_resume_instance = MagicMock()
        # Set id to string instead of MagicMock to avoid serialization issues
        mock_resume_instance.id = "resume123"
        mock_resume.return_value = mock_resume_instance
        
        # Make request
        response = client.post(
            '/resumes',
            data=json.dumps(sample_resume_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data["message"] == "Resume created successfully!"
        assert response_data["resume_id"] == "resume123"
        
        # Verify mock was called correctly
        mock_resume.assert_called_once_with(**sample_resume_data)
        mock_resume_instance.save.assert_called_once()


class TestGetResumeById:
    
    @patch('routes.resume.Resume.find_by_id')
    def test_get_resume_success(self, mock_find_by_id, client, sample_resume_data):
        """Test successfully retrieving a resume by ID"""
        # Setup mock
        mock_resume = MagicMock()
        mock_resume.dict.return_value = {
            "_id": "resume123",
            **sample_resume_data
        }
        mock_find_by_id.return_value = mock_resume
        
        # Make request
        response = client.get('/resumes/resume123')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data["user_id"] == sample_resume_data["user_id"]
        assert response_data["fName"] == sample_resume_data["fName"]
        
        # Verify mock was called correctly
        mock_find_by_id.assert_called_once_with("resume123")

    @patch('routes.resume.Resume.find_by_id')
    def test_get_resume_not_found(self, mock_find_by_id, client):
        """Test getting a non-existent resume"""
        # Setup mock
        mock_find_by_id.return_value = None
        
        # Make request
        response = client.get('/resumes/nonexistent_resume')
        
        # Assert response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert response_data["error"] == "Resume not found"
        
        # Verify mock was called correctly
        mock_find_by_id.assert_called_once_with("nonexistent_resume")

    


class TestImproveResume:
    
    @patch('routes.resume.enhance_resume_with_deepseek')
    @patch('routes.resume.Resume.find_by_id')
    def test_improve_resume_success(self, mock_find_by_id, mock_enhance, client, sample_resume_data):
        """Test successfully improving a resume"""
        # Setup mocks with proper strings for id - avoid MagicMock objects
        mock_resume = MagicMock()
        mock_resume.id = "resume123"  # String instead of MagicMock
        mock_resume.dict.return_value = sample_resume_data
        mock_find_by_id.return_value = mock_resume
        
        # Mock AI response
        mock_enhance.return_value = {
            "improved_resume": "Improved resume content here...",
            "ats_score": 85
        }
        
        # Make request
        response = client.post('/resumes/resume123/improve')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data["message"] == "Resume improved successfully!"
        assert response_data["resume_id"] == "resume123"
        assert response_data["ai_enhanced_resume"] == "Improved resume content here..."
        assert response_data["ats_score"] == 85
        
        # Verify mocks were called correctly
        mock_find_by_id.assert_called_once_with("resume123")
        mock_enhance.assert_called_once()
        mock_resume.save.assert_called_once()

    @patch('routes.resume.Resume.find_by_id')
    def test_improve_resume_not_found(self, mock_find_by_id, client):
        """Test improving a non-existent resume"""
        # Setup mock
        mock_find_by_id.return_value = None
        
        # Make request
        response = client.post('/resumes/nonexistent_resume/improve')
        
        # Assert response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert response_data["error"] == "Resume not found"
        
        # Verify mock was called correctly
        mock_find_by_id.assert_called_once_with("nonexistent_resume")

    # Fix for JSON serialization error
    @patch('routes.resume.enhance_resume_with_deepseek')
    @patch('routes.resume.Resume.find_by_id')
    def test_improve_resume_ai_error(self, mock_find_by_id, mock_enhance, client, sample_resume_data):
        """Test resume improvement when AI returns an error"""
        # Setup mocks with proper string values instead of MagicMock objects
        mock_resume = MagicMock()
        mock_resume.id = "resume123"  # String instead of MagicMock
        mock_resume.dict.return_value = sample_resume_data
        mock_resume.ai_enhanced_resume = ""  # Provide string values
        mock_resume.ats_score = 0  # Provide numeric values
        mock_find_by_id.return_value = mock_resume
        
        # Mock AI error
        mock_enhance.return_value = {
            "error": "AI processing failed"
        }
        
        # Make request
        response = client.post('/resumes/resume123/improve')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data["message"] == "Resume improved successfully!"
        assert response_data["ai_enhanced_resume"] == ""  # Default value when AI doesn't provide one
        assert response_data["ats_score"] == 0  # Default value when AI doesn't provide one
        
        # Verify save still happened with default values
        mock_resume.save.assert_called_once()

   