import pytest
import json
import io
from unittest.mock import patch, MagicMock
from flask import Flask
from bson import ObjectId
import datetime
from routes.quiz_ai import quiz_ai_routes

# Constant valid ObjectId strings for testing
VALID_QUIZ_ID = "507f1f77bcf86cd799439011"  # 24-char hex string
VALID_USER_ID = "507f1f77bcf86cd799439012"
VALID_RESPONSE_ID = "507f1f77bcf86cd799439013"

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(quiz_ai_routes)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestGetQuestions:
    
    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.generate_questions')
    def test_get_questions_success_with_topic(self, mock_generate_questions, mock_get_profile, client):
        """Test getting questions successfully with a topic."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": "user123",
            "preferredLanguage": "en"
        })
        
        # Mock question generation
        mock_generate_questions.return_value = {
            "quiz_id": "quiz123",
            "questions": [
                {"question_id": "q1", "question": "What is 2+2?", "correct_answer": "4"}
            ]
        }
        
        # Create test data
        data = {"topic": "Mathematics", "num": "5", "level": "easy"}
        
        # Make request
        response = client.post(
            '/ai/quiz/user123',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "quiz_id" in response_data
        assert "questions" in response_data
        
        # Verify mocks called correctly
        mock_get_profile.assert_called_once_with("user123")
        mock_generate_questions.assert_called_once_with(
            "user123", "Mathematics", None, None, 5, "easy", language="en"
        )

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.ALLOWED_MIME_TYPES', ["application/pdf"])
    @patch('routes.quiz_ai.generate_questions')
    def test_get_questions_success_with_file(self, mock_generate_questions, mock_get_profile, client):
        """Test getting questions successfully with a file."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": "user123",
            "preferredLanguage": "fr"
        })
        
        # Mock question generation
        mock_generate_questions.return_value = {
            "quiz_id": "quiz456",
            "questions": [
                {"question_id": "q1", "question": "Qu'est-ce que 2+2?", "correct_answer": "4"}
            ]
        }
        
        # Create test file
        file_content = b"This is a test PDF file content"
        test_file = (io.BytesIO(file_content), "test.pdf", "application/pdf")
        
        # Make request with file
        data = {"level": "medium"}
        response = client.post(
            '/ai/quiz/user123',
            data={**data, "file": test_file},
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "quiz_id" in response_data
        assert "questions" in response_data
        
        # Verify mocks called correctly with file content
        mock_get_profile.assert_called_once_with("user123")
        # Can't directly check file_content because it's read in the route, 
        # but we can verify other params
        mock_generate_questions.assert_called_once()
        args, kwargs = mock_generate_questions.call_args
        assert args[0] == "user123"  # user_id
        assert args[1] is None  # topic
        assert args[4] == 5  # default num_questions
        assert args[5] == "medium"  # level
        assert kwargs["language"] == "fr"  # preferred language

    def test_get_questions_no_data(self, client):
        """Test getting questions with no data provided."""
        # Make request with no data
        response = client.post('/ai/quiz/user123')
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "No data provided" in response_data["error"]

    def test_get_questions_invalid_level(self, client):
        """Test getting questions with invalid difficulty level."""
        # Create test data with invalid level
        data = {"topic": "Mathematics", "level": "super_hard"}
        
        # Make request
        response = client.post(
            '/ai/quiz/user123',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Invalid level" in response_data["error"]

    @patch('routes.quiz_ai.ALLOWED_MIME_TYPES', ["application/pdf"])
    def test_get_questions_unsupported_file_type(self, client):
        """Test getting questions with unsupported file type."""
        # Create test file with unsupported type
        file_content = b"This is a test file content"
        test_file = (io.BytesIO(file_content), "test.exe", "application/octet-stream")
        
        # Make request with file
        data = {"topic": "Mathematics"}
        response = client.post(
            '/ai/quiz/user123',
            data={**data, "file": test_file},
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Unsupported file type" in response_data["error"]

    @patch('routes.quiz_ai.ALLOWED_MIME_TYPES', ["application/pdf"])
    def test_get_questions_file_too_large(self, client):
        """Test getting questions with file exceeding size limit."""
        # Create large file (11MB)
        large_file_content = b"x" * (11 * 1024 * 1024)
        large_file = (io.BytesIO(large_file_content), "large.pdf", "application/pdf")
        
        # Make request with large file
        data = {"topic": "Mathematics"}
        response = client.post(
            '/ai/quiz/user123',
            data={**data, "file": large_file},
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "File size exceeds" in response_data["error"]

    def test_get_questions_no_topic_or_file(self, client):
        """Test getting questions with neither topic nor file."""
        # Create test data with no topic
        data = {"level": "easy"}  # Only level, no topic or file
        
        # Make request
        response = client.post(
            '/ai/quiz/user123',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "At least one of 'topic' or 'file' must be provided" in response_data["error"]

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    def test_get_questions_user_not_found(self, mock_get_profile, client):
        """Test getting questions when user profile is not found."""
        # Mock user profile not found
        mock_get_profile.return_value = None
        
        # Create test data
        data = {"topic": "Mathematics"}
        
        # Make request
        response = client.post(
            '/ai/quiz/invalid_user',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "User profile not found" in response_data["error"]

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.generate_questions')
    def test_get_questions_generation_error(self, mock_generate_questions, mock_get_profile, client):
        """Test getting questions when there's an error in generation."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": "user123",
            "preferredLanguage": "en"
        })
        
        # Mock question generation error
        mock_generate_questions.return_value = {
            "error": "Failed to generate questions"
        }
        
        # Create test data
        data = {"topic": "Mathematics"}
        
        # Make request
        response = client.post(
            '/ai/quiz/user123',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Failed to generate questions" in response_data["error"]


class TestSubmitAnswers:
    
    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.get_azure_openai_llm')
    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_success_first_submission(self, mock_mongodb, mock_llm, mock_get_profile, client):
        """Test successful first-time answer submission."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": VALID_USER_ID,
            "preferredLanguage": "en"
        })
        
        # Mock LLM for feedback
        mock_llm_instance = MagicMock()
        mock_llm_instance.return_value.content = "Good try, but the correct answer is 4."
        mock_llm.return_value = mock_llm_instance
        
        # Mock MongoDB client and session
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.start_session.return_value.__enter__.return_value = mock_session
        mock_client.__getitem__.return_value = mock_db
        
        # Mock quiz in database
        quiz = {
            "_id": ObjectId(VALID_QUIZ_ID),
            "user_id": VALID_USER_ID,
            "questions": [
                {"question_id": "q1", "question": "What is 2+2?", "question_type": "MC", "correct_answer": "4"},
                {"question_id": "q2", "question": "What is the capital of France?", "question_type": "SA", "correct_answer": "Paris"}
            ]
        }
        mock_db.quizzes.find_one.return_value = quiz
        
        # Mock no previous submission
        mock_db.user_responses.find_one.return_value = None
        
        # Mock successful insert
        mock_db.user_responses.insert_one.return_value.inserted_id = ObjectId(VALID_RESPONSE_ID)
        
        # Mock user update
        mock_db.users.update_one.return_value.modified_count = 1
        
        # Mock fetching updated user score
        mock_db.users.find_one.return_value = {"_id": ObjectId(VALID_USER_ID), "total_score": 20}
        
        # Test data
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "q1", "user_answer": "4"},
                {"question_id": "q2", "user_answer": "Paris"}
            ]
        }
        
        # Make request
        response = client.post(
            f'/ai/quiz/{VALID_QUIZ_ID}/submit',
            data=json.dumps(answers_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "response_id" in response_data
        assert "score" in response_data
        assert response_data["score"] == 20  # 10 points for each correct answer
        assert response_data["total_possible_points"] == 20  # 2 questions * 10 points
        assert "feedback" in response_data
        assert response_data["total_score"] == 20  # Updated total score
        
        # Verify transaction was used
        mock_session.start_transaction.assert_called_once()

    def test_submit_answers_missing_user_id(self, client):
        """Test submitting answers with missing user_id."""
        # Test data with missing user_id
        answers_data = {
            "answers": [
                {"question_id": "q1", "user_answer": "4"}
            ]
        }
        
        # Make request
        response = client.post(
            f'/ai/quiz/{VALID_QUIZ_ID}/submit',
            data=json.dumps(answers_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "user_id and answers are required" in response_data["error"]

    def test_submit_answers_missing_answers(self, client):
        """Test submitting with missing answers."""
        # Test data with missing answers
        answers_data = {
            "user_id": VALID_USER_ID
        }
        
        # Make request
        response = client.post(
            f'/ai/quiz/{VALID_QUIZ_ID}/submit',
            data=json.dumps(answers_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "user_id and answers are required" in response_data["error"]

    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_quiz_not_found(self, mock_mongodb, client):
        """Test submitting answers when quiz is not found."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock quiz not found
        mock_db.quizzes.find_one.return_value = None
        
        # Test data
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "q1", "user_answer": "4"}
            ]
        }
        
        # Make request
        response = client.post(
            f'/ai/quiz/{VALID_QUIZ_ID}/submit',
            data=json.dumps(answers_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Quiz not found" in response_data["error"]

    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_not_all_answered(self, mock_mongodb, client):
        """Test submitting answers when not all questions are answered."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock quiz with 2 questions
        quiz = {
            "_id": ObjectId(VALID_QUIZ_ID),
            "user_id": VALID_USER_ID,
            "questions": [
                {"question_id": "q1", "question": "What is 2+2?", "correct_answer": "4"},
                {"question_id": "q2", "question": "What is the capital of France?", "correct_answer": "Paris"}
            ]
        }
        mock_db.quizzes.find_one.return_value = quiz

        # Test data with only 1 answer
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "q1", "user_answer": "4"}
                # Missing answer for q2
            ]
        }
        
        # Make request
        response = client.post(
            f'/ai/quiz/{VALID_QUIZ_ID}/submit',
            data=json.dumps(answers_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "All 2 questions must be answered" in response_data["error"]

    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_invalid_question_id(self, mock_mongodb, client):
        """Test submitting answers with invalid question_id."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock quiz
        quiz = {
            "_id": ObjectId(VALID_QUIZ_ID),
            "user_id": VALID_USER_ID,
            "questions": [
                {"question_id": "q1", "question": "What is 2+2?", "correct_answer": "4"}
            ]
        }
        mock_db.quizzes.find_one.return_value = quiz
        
        # Test data with invalid question_id
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "invalid_question", "user_answer": "4"}
            ]
        }
        
        # Make request
        response = client.post(
            f'/ai/quiz/{VALID_QUIZ_ID}/submit',
            data=json.dumps(answers_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Invalid question_id" in response_data["error"]

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_user_profile_not_found(self, mock_mongodb, mock_get_profile, client):
        """Test submitting answers when user profile is not found."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock quiz
        quiz = {
            "_id": ObjectId(VALID_QUIZ_ID),
            "user_id": VALID_USER_ID,
            "questions": [
                {"question_id": "q1", "question": "What is 2+2?", "correct_answer": "4"}
            ]
        }
        mock_db.quizzes.find_one.return_value = quiz
        
        # Mock user profile not found
        mock_get_profile.return_value = None
        
        # Test data
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "q1", "user_answer": "4"}
            ]
        }
        
        # Make request
        response = client.post(
            f'/ai/quiz/{VALID_QUIZ_ID}/submit',
            data=json.dumps(answers_data),
            content_type='application/json'
        )
        
        # Assert response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "User profile not found" in response_data["error"]


class TestGetTotalScore:
    
    @patch('routes.quiz_ai.MongoDBClient')
    @patch('routes.quiz_ai.ObjectId')  # Add this to patch ObjectId
    def test_get_total_score_success(self, mock_objectid, mock_mongodb, client):
        """Test successfully retrieving a user's total score."""
        # Mock ObjectId to handle string conversion
        mock_objectid.return_value = ObjectId(VALID_USER_ID)
        
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock user with total_score
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(VALID_USER_ID),
            "total_score": 150
        }
        
        # Make request
        response = client.get(f'/ai/user/{VALID_USER_ID}/total_score')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "total_score" in response_data
        assert response_data["total_score"] == 150
    
    @patch('routes.quiz_ai.MongoDBClient')
    @patch('routes.quiz_ai.ObjectId')  # Add this to patch ObjectId
    def test_get_total_score_user_not_found(self, mock_objectid, mock_mongodb, client):
        """Test getting total score when user is not found."""
        # Mock ObjectId to handle string conversion
        mock_objectid.return_value = ObjectId(VALID_USER_ID)
        
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock user not found
        mock_db.users.find_one.return_value = None
        
        # Make request
        response = client.get(f'/ai/user/{VALID_USER_ID}/total_score')
        
        # Assert response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "User not found" in response_data["error"]
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_total_score_exception(self, mock_mongodb, client):
        """Test getting total score when an exception occurs."""
        # Patch at a lower level to avoid ObjectId validation
        with patch('routes.quiz_ai.ObjectId', side_effect=Exception("Database connection error")):
            # Make request
            response = client.get(f'/ai/user/{VALID_USER_ID}/total_score')
            
            # Assert response
            assert response.status_code == 500
            response_data = json.loads(response.data)
            assert "error" in response_data
            assert "Failed to retrieve total score" in response_data["error"]

    @patch('routes.quiz_ai.MongoDBClient')
    @patch('routes.quiz_ai.ObjectId')  # Add this to patch ObjectId
    def test_get_total_score_default_zero(self, mock_objectid, mock_mongodb, client):
        """Test getting total score when it's not present in the user document."""
        # Mock ObjectId to handle string conversion
        mock_objectid.return_value = ObjectId(VALID_USER_ID)
        
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock user without total_score field
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(VALID_USER_ID)
            # No total_score field
        }
        
        # Make request
        response = client.get(f'/ai/user/{VALID_USER_ID}/total_score')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "total_score" in response_data
        assert response_data["total_score"] == 0