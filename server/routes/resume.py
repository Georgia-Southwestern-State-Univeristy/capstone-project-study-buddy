from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from agents.resume_ai_agent import enhance_resume_with_deepseek

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

@resume_routes.route("/resumes/<resume_id>/improve", methods=["POST"])
def improve_resume(resume_id):
    """
    POST /resumes/<resume_id>/improve
    1) Fetch the existing resume.
    2) Send data to AI agent for improvement & ATS scoring.
    3) Store improved text & score directly in DB.
    4) Return the updated resume to the client.
    """
    # 1. Fetch from DB
    resume_obj = Resume.find_by_id(resume_id)
    if not resume_obj:
        return jsonify({"error": "Resume not found"}), 404

    # 2. Convert to dict
    resume_dict = resume_obj.dict(exclude={"id", "created_at", "updated_at", "ai_enhanced_resume", "ats_score"})

    # 3. Call AI
    ai_result = enhance_resume_with_deepseek(resume_dict)
    improved_resume = ai_result.get("improved_resume", "")
    ats_score = ai_result.get("ats_score", 0)

    # 4. Store in DB
    resume_obj.ai_enhanced_resume = improved_resume
    resume_obj.ats_score = ats_score
    resume_obj.save()

    # 5. Return updated info
    return jsonify({
        "message": "Resume improved successfully!",
        "resume_id": resume_obj.id,
        "ai_enhanced_resume": resume_obj.ai_enhanced_resume,
        "ats_score": resume_obj.ats_score
    }), 200

