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
        
        # Verify mocks called correctly - updated to match actual function signature
        mock_get_profile.assert_called_once_with("user123")
        mock_generate_questions.assert_called_once_with(
            "user123", "Mathematics", None, None, None, 5, "easy", language="en"
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
        assert args[2] is None  # sub_topic 
        # Skip checking file_content at args[3]
        assert args[4] == "application/pdf"  # file_mime_type
        assert args[5] == 5  # num_questions - fixed position from 4 to 5
        assert args[6] == "medium"  # level
        assert kwargs["language"] == "fr"  # preferred language

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.generate_questions')
    def test_get_questions_with_subtopic(self, mock_generate_questions, mock_get_profile, client):
        """Test getting questions successfully with a topic and subtopic."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": "user123",
            "preferredLanguage": "en"
        })
        
        # Mock question generation
        mock_generate_questions.return_value = {
            "quiz_id": "quiz123",
            "questions": [
                {"question_id": "q1", "question": "What is a cell?", "correct_answer": "The basic unit of life"}
            ]
        }
        
        # Create test data with subtopic
        data = {"topic": "Biology", "sub_topic": "Cell Structure", "level": "medium"}
        
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
        
        # Verify subtopic was passed correctly
        mock_generate_questions.assert_called_once_with(
            "user123", "Biology", "Cell Structure", None, None, 5, "medium", language="en"
        )

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.ALLOWED_MIME_TYPES', ["application/pdf"])
    @patch('routes.quiz_ai.generate_questions')
    def test_get_questions_with_topic_and_file(self, mock_generate_questions, mock_get_profile, client):
        """Test getting questions with both a topic and file provided."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": "user123",
            "preferredLanguage": "en"
        })
        
        # Mock question generation
        mock_generate_questions.return_value = {
            "quiz_id": "quiz789",
            "questions": [
                {"question_id": "q1", "question": "What are mitochondria?", "correct_answer": "Powerhouse of the cell"}
            ]
        }
        
        # Create test file
        file_content = b"This is a test PDF file about cell biology"
        test_file = (io.BytesIO(file_content), "cell_biology.pdf", "application/pdf")
        
        # Make request with both topic and file
        data = {"topic": "Biology", "level": "hard"}
        response = client.post(
            '/ai/quiz/user123',
            data={**data, "file": test_file},
            content_type='multipart/form-data'
        )
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "quiz_id" in response_data
        
        # Verify both topic and file content were used
        mock_generate_questions.assert_called_once()
        args, kwargs = mock_generate_questions.call_args
        assert args[0] == "user123"  # user_id
        assert args[1] == "Biology"  # topic
        assert args[4] == "application/pdf"  # file_mime_type
        assert args[6] == "hard"  # level
        assert kwargs["language"] == "en"

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.generate_questions')
    def test_get_questions_custom_number(self, mock_generate_questions, mock_get_profile, client):
        """Test getting a custom number of questions."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": "user123",
            "preferredLanguage": "en"
        })
        
        # Mock question generation
        mock_generate_questions.return_value = {
            "quiz_id": "quiz123",
            "questions": [{"question_id": f"q{i}", "question": f"Question {i}"} for i in range(1, 11)]
        }
        
        # Create test data with custom number of questions
        data = {"topic": "History", "num": "10", "level": "easy"}
        
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
        
        # Verify custom number was passed correctly
        mock_generate_questions.assert_called_once_with(
            "user123", "History", None, None, None, 10, "easy", language="en"
        )

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

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.get_azure_openai_llm')
    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_resubmission(self, mock_mongodb, mock_llm, mock_get_profile, client):
        """Test behavior when submitting answers to the same quiz again."""
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
        
        # Mock previous submission exists
        mock_db.user_responses.find_one.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439014"),
            "quiz_id": VALID_QUIZ_ID,
            "user_id": VALID_USER_ID,
            "score": 10,  # Previously got 1 question correct
            "answers": [
                {"question_id": "q1", "user_answer": "4"},
                {"question_id": "q2", "user_answer": "London"}
            ]
        }
        
        # Mock successful insert for new submission
        mock_db.user_responses.insert_one.return_value.inserted_id = ObjectId(VALID_RESPONSE_ID)
        
        # Mock user score (should not change on resubmission)
        mock_db.users.find_one.return_value = {"_id": ObjectId(VALID_USER_ID), "total_score": 10}
        
        # Test data for resubmission with different answers
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "q1", "user_answer": "4"},
                {"question_id": "q2", "user_answer": "Paris"}  # Now correct
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
        
        # User's total score should not change for resubmission
        assert response_data["total_score"] == 10
        
        # Verify users collection was NOT updated (no $inc operation on resubmission)
        mock_db.users.update_one.assert_not_called()

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.get_azure_openai_llm')
    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_mixed_question_types(self, mock_mongodb, mock_llm, mock_get_profile, client):
        """Test submitting answers with a mix of MC and SA questions."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": VALID_USER_ID,
            "preferredLanguage": "es"  # Spanish
        })
        
        # Mock LLM for feedback
        mock_llm_instance = MagicMock()
        mock_llm_instance.return_value.content = "La respuesta correcta es Berlín."
        mock_llm.return_value = mock_llm_instance
        
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.start_session.return_value.__enter__.return_value = mock_session
        mock_client.__getitem__.return_value = mock_db
        
        # Mock quiz with mixed question types
        quiz = {
            "_id": ObjectId(VALID_QUIZ_ID),
            "user_id": VALID_USER_ID,
            "questions": [
                {"question_id": "q1", "question": "¿Cuánto es 2+2?", "question_type": "MC", "correct_answer": "4"},
                {"question_id": "q2", "question": "¿Cuál es la capital de Alemania?", "question_type": "SA", "correct_answer": "Berlín"}
            ]
        }
        mock_db.quizzes.find_one.return_value = quiz
        
        # Mock no previous submission
        mock_db.user_responses.find_one.return_value = None
        
        # Mock successful insert
        mock_db.user_responses.insert_one.return_value.inserted_id = ObjectId(VALID_RESPONSE_ID)
        
        # Mock user update
        mock_db.users.update_one.return_value.modified_count = 1
        
        # Mock updated user score
        mock_db.users.find_one.return_value = {"_id": ObjectId(VALID_USER_ID), "total_score": 10}
        
        # Test data - correct MC answer but wrong SA answer
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "q1", "user_answer": "4"},  # Correct MC answer
                {"question_id": "q2", "user_answer": "Madrid"}  # Wrong SA answer
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
        
        # Score should be 5 (10 for correct MC, -5 for wrong SA, total 5)
        assert response_data["score"] == 5
        
        # Verify LLM was called with Spanish prompt for feedback
        mock_llm.return_value.assert_called_once()
        call_args = mock_llm.return_value.call_args[0][0]
        assert "Spanish" in call_args

    @patch('routes.quiz_ai.get_user_profile_by_user_id')
    @patch('routes.quiz_ai.is_similar')
    @patch('routes.quiz_ai.get_azure_openai_llm')
    @patch('routes.quiz_ai.MongoDBClient')
    def test_submit_answers_with_similar_sa_answer(self, mock_mongodb, mock_llm, mock_is_similar, mock_get_profile, client):
        """Test submitting a short answer that is similar but not exact."""
        # Mock user profile
        mock_get_profile.return_value = json.dumps({
            "_id": VALID_USER_ID,
            "preferredLanguage": "en"
        })
        
        # Mock LLM for feedback
        mock_llm_instance = MagicMock()
        mock_llm_instance.return_value.content = "Your answer is correct!"
        mock_llm.return_value = mock_llm_instance
        
        # Mock is_similar to return True for the test case
        mock_is_similar.return_value = True
        
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.start_session.return_value.__enter__.return_value = mock_session
        mock_client.__getitem__.return_value = mock_db
        
        # Mock quiz
        quiz = {
            "_id": ObjectId(VALID_QUIZ_ID),
            "user_id": VALID_USER_ID,
            "questions": [
                {"question_id": "q1", "question": "What is the capital of France?", "question_type": "SA", "correct_answer": "Paris"}
            ]
        }
        mock_db.quizzes.find_one.return_value = quiz
        
        # Mock no previous submission
        mock_db.user_responses.find_one.return_value = None
        
        # Mock successful insert
        mock_db.user_responses.insert_one.return_value.inserted_id = ObjectId(VALID_RESPONSE_ID)
        
        # Mock user update
        mock_db.users.update_one.return_value.modified_count = 1
        
        # Mock updated user score
        mock_db.users.find_one.return_value = {"_id": ObjectId(VALID_USER_ID), "total_score": 10}
        
        # Test data with similar but not exact SA answer
        answers_data = {
            "user_id": VALID_USER_ID,
            "answers": [
                {"question_id": "q1", "user_answer": "paris"}  # Similar to "Paris" (lowercase)
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
        
        # Should be marked as correct due to similarity
        assert response_data["score"] == 10
        
        # Verify similarity check was called
        mock_is_similar.assert_called_once_with("paris", "paris")

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


class TestGetTopicScores:
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_topic_scores_success(self, mock_mongodb, client):
        """Test successfully retrieving a user's topic scores."""
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
        
        # Mock response count
        mock_db.user_responses.count_documents.return_value = 3
        
        # Mock aggregation result
        mock_db.user_responses.aggregate.return_value = [
            {"topic": "Math", "score": 50, "quiz_count": 1},
            {"topic": "Science", "score": 70, "quiz_count": 2},
            {"topic": "History", "score": 30, "quiz_count": 1}
        ]
        
        # Make request
        response = client.get(f'/ai/{VALID_USER_ID}/topic_scores')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "topic_scores" in response_data
        assert "total_score" in response_data
        assert "quiz_count" in response_data
        assert len(response_data["topic_scores"]) == 3
        assert response_data["total_score"] == 150
        assert response_data["quiz_count"] == 3
        
        # Verify the topic scores
        topics = [topic["topic"] for topic in response_data["topic_scores"]]
        assert "Math" in topics
        assert "Science" in topics
        assert "History" in topics
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_topic_scores_no_quizzes(self, mock_mongodb, client):
        """Test getting topic scores when user has no quizzes."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock user with total_score
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(VALID_USER_ID),
            "total_score": 0
        }
        
        # Mock response count = 0 (no quizzes)
        mock_db.user_responses.count_documents.return_value = 0
        
        # Make request
        response = client.get(f'/ai/{VALID_USER_ID}/topic_scores')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "topic_scores" in response_data
        assert len(response_data["topic_scores"]) == 0  # Empty list
        assert "message" in response_data
        assert "User has not completed any quizzes yet" in response_data["message"]
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_topic_scores_user_not_found(self, mock_mongodb, client):
        """Test getting topic scores when user is not found."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock user not found
        mock_db.users.find_one.return_value = None
        
        # Make request
        response = client.get(f'/ai/{VALID_USER_ID}/topic_scores')
        
        # Assert response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "User not found" in response_data["error"]
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_topic_scores_exception(self, mock_mongodb, client):
        """Test getting topic scores when an exception occurs."""
        # Mock MongoDB client to raise exception on aggregation
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock user found
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(VALID_USER_ID),
            "total_score": 50
        }
        
        # Mock response count
        mock_db.user_responses.count_documents.return_value = 2
        
        # Mock aggregation exception
        mock_db.user_responses.aggregate.side_effect = Exception("Database error")
        
        # Make request
        response = client.get(f'/ai/{VALID_USER_ID}/topic_scores')
        
        # Assert response
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Failed to retrieve topic scores" in response_data["error"]


class TestGetScoreboard:
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_scoreboard_success(self, mock_mongodb, client):
        """Test successfully retrieving the scoreboard."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock counts
        mock_db.user_responses.count_documents.return_value = 10
        mock_db.quizzes.count_documents.return_value = 5
        
        # Mock aggregation result
        mock_db.user_responses.aggregate.return_value = [
            {"user_id": "user1", "username": "Alice", "total_score": 120, "quiz_count": 3},
            {"user_id": "user2", "username": "Bob", "total_score": 100, "quiz_count": 2},
            {"user_id": "user3", "username": "Charlie", "total_score": 80, "quiz_count": 2}
        ]
        
        # Make request
        response = client.get('/ai/scoreboard')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "leaderboard" in response_data
        assert "meta" in response_data
        
        # Verify the leaderboard data
        leaderboard = response_data["leaderboard"]
        assert len(leaderboard) == 3
        assert leaderboard[0]["username"] == "Alice"  # Top scorer
        assert leaderboard[0]["total_score"] == 120
        assert leaderboard[1]["username"] == "Bob"    # Second place
        assert leaderboard[2]["username"] == "Charlie"  # Third place
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_scoreboard_empty(self, mock_mongodb, client):
        """Test getting scoreboard when there are no responses."""
        # Mock MongoDB client
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock empty counts
        mock_db.user_responses.count_documents.return_value = 0
        mock_db.quizzes.count_documents.return_value = 0
        
        # Mock empty aggregation result
        mock_db.user_responses.aggregate.return_value = []
        
        # Mock sample data for debugging - fix the way cursor is mocked
        mock_response_cursor = MagicMock()
        mock_response_cursor.limit.return_value = []
        mock_db.user_responses.find.return_value = mock_response_cursor
        
        mock_users_cursor = MagicMock()
        mock_users_cursor.limit.return_value = []
        mock_db.users.find.return_value = mock_users_cursor
        
        # Make request
        response = client.get('/ai/scoreboard')
        
        # Assert response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "leaderboard" in response_data
        assert len(response_data["leaderboard"]) == 0  # Empty leaderboard
        assert "meta" in response_data
        assert response_data["meta"]["total_users"] == 0
    
    @patch('routes.quiz_ai.MongoDBClient')
    def test_get_scoreboard_exception(self, mock_mongodb, client):
        """Test getting scoreboard when an exception occurs."""
        # Mock MongoDB client to raise exception
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_mongodb.get_client.return_value = mock_client
        mock_mongodb.get_db_name.return_value = "test_db"
        mock_client.__getitem__.return_value = mock_db
        
        # Mock aggregation exception
        mock_db.user_responses.aggregate.side_effect = Exception("Database error")
        
        # Make request
        response = client.get('/ai/scoreboard')
        
        # Assert response
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Failed to generate scoreboard" in response_data["error"]