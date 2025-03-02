from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from models.resume import Resume

resume_routes = Blueprint("resume", __name__)

@resume_routes.route("/resumes", methods=["POST"])
def create_resume():
    """
    POST /resumes
    {
      "user_id": "...",
      "fName": "...",
      "lName": "...",
      ...
      "socialAccounts": [
        {"platform": "LinkedIn", "handle": "@john_doe", "link": "https://..."}
      ],
      "education": [...],
      "experience": [...],
      "projects": [...],
      "references": [...]
    }
    Validates the data, saves to DB, and returns JSON confirming creation.
    """
    # 1. Parse JSON body
    payload = request.get_json(force=True) or {}

    # 2. Validate user inputs with Pydantic
    try:
        new_resume = Resume(**payload)
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 400

    # 3. Persist to DB
    new_resume.save()

    # 4. Return a success response
    return jsonify({
        "message": "Resume created successfully!",
        "resume_id": new_resume.id
    }), 201


# Example additional route
@resume_routes.route("/resumes/<resume_id>", methods=["GET"])
def get_resume_by_id(resume_id):
    resume_obj = Resume.find_by_id(resume_id)
    if not resume_obj:
        return jsonify({"error": "Resume not found"}), 404
    return jsonify(resume_obj.dict()), 200
