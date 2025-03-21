"""This module defines the routes for the AI Mentor."""

"""Step 1: Import necessary modules"""
import logging
from flask import jsonify, Blueprint, request
import json
from agents.meme_mingle_agent_avtar import MemeMingleAIAgent
from services.azure_mongodb import MongoDBClient
import filetype
from services.azure_form_recognizer import ALLOWED_MIME_TYPES


"""Step 2: Create a Blueprint object"""
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_avtar_routes = Blueprint("ai_avtar", __name__)



"""Step 3: Define the routes"""

# Define the route for the initial greeting with role input
@ai_avtar_routes.post("/ai_mentor_avtar/welcome/<user_id>")
def get_mental_health_agent_welcome(user_id):
    body = request.get_json()
    if not body:
        return jsonify({"error": "No data provided"}), 400
    
    desired_role = body.get("role", "Education")  # Default to 'educational mentor' if not specified

    agent = MemeMingleAIAgent(
        tool_names=[
            "gutendex_textbook_search",
            "generate_suggestions",
            "web_search_tavily",
            "location_search_gplaces",
            "textbook_search",
            "user_profile_retrieval",
            "agent_facts",
            "generate_document",
            "job_search",
            "web_search_bing",
            "fetch_meme",
        ],
        desired_role=desired_role  # Pass the desired role to the agent
    )

    response = agent.get_initial_greeting(user_id=user_id)

    if response is None:
        logger.error(f"No greeting found for user {user_id}")
        return jsonify({"error": "Greeting not found"}), 404

    return jsonify(response), 200



# Define the route for the main conversation
@ai_avtar_routes.post("/ai_mentor_avtar/<user_id>/<chat_id>")
def run_mental_health_agent(user_id, chat_id):
    body = request.form.to_dict()
    if not body:
        return jsonify({"error": "No data provided"}), 400

    prompt = body.get("prompt")
    turn_id = int(body.get("turn_id", 0))

    # Check for file in the request
    uploaded_file = request.files.get('file')

    # Handle the uploaded file
    file_content = None
    file_mime_type = None
    if uploaded_file:
        # Read the file content
        file_content = uploaded_file.read()

        # Detect the file type using 'filetype'
        kind = filetype.guess(file_content)
        if kind is None:
            return jsonify({'error': 'Cannot guess the file type'}), 400

        
        file_mime_type = kind.mime

        print(f"allowed mime types: {ALLOWED_MIME_TYPES}")
        if file_mime_type not in ALLOWED_MIME_TYPES:
            return jsonify({'error': f'Unsupported file type: {file_mime_type}'}), 400

        # Implement file size check
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        if len(file_content) > MAX_FILE_SIZE:
            return jsonify({'error': 'File size exceeds the maximum limit of 10 MB'}), 400

    # Retrieve desired_role from the database
    db_client = MongoDBClient.get_client()
    db_name = MongoDBClient.get_db_name()
    db = db_client[db_name]
    chat_summary_collection = db["chat_summaries"]
    chat_summary = chat_summary_collection.find_one({"user_id": user_id, "chat_id": int(chat_id)})
    desired_role = chat_summary.get("desired_role", "Education")
    print(f"Desired role: {desired_role}")
    agent = MemeMingleAIAgent(
        tool_names=[
            "gutendex_textbook_search",
            "generate_suggestions",
            "web_search_tavily",
            "location_search_gplaces",
            "textbook_search",
            "user_profile_retrieval",
            "agent_facts",
            "generate_document",
            "job_search",
            "web_search_bing",
            "fetch_meme",
        ],
        desired_role=desired_role  
    )

    try:
            
        response = agent.run(
                                file_content=file_content,
                                file_mime_type=file_mime_type,
                                message=prompt,
                                with_history=True,
                                user_id=user_id,
                                chat_id=int(chat_id),
                                turn_id=turn_id + 1, 
                            )

        return jsonify(response), 200
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500



# Define the route for finalizing the conversation
@ai_avtar_routes.patch("/ai_mentor_avtar/finalize/<user_id>/<chat_id>")
def set_mental_health_end_state(user_id, chat_id):
    try:
        logger.info(f"Finalizing chat {chat_id} for user {user_id}")
        agent = MemeMingleAIAgent(tool_names=["gutendex_textbook_search","generate_suggestions","web_search_youtube","web_search_tavily","textbook_search","location_search_gplaces", "web_search_google", "user_profile_retrieval", "agent_facts"])

        agent.perform_final_processes(user_id, chat_id)

        # Potentially update the database or perform other cleanup operations
        # For now, let's assume it's a simple response:
        return jsonify({"message": "Chat session finalized successfully"}), 200

    except Exception as e:
        logger.error(f"Error during finalizing chat: {e}", exc_info=True)
        return jsonify({"error": "Failed to finalize chat"}), 500
    