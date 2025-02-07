from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from models.study_group import StudyGroup
from models.user import User  # <-- Import your User model
from services.azure_mongodb import MongoDBClient

groups_routes = Blueprint("groups", __name__)

@groups_routes.route("/groups/create", methods=["POST"])
def create_group():
    try:
        # 1. Get JSON payload
        payload = request.get_json(force=True)

        # 2. If payload has a 'created_by' field and we want them as an admin:
        if payload.get("created_by"):
            if not payload.get("admins"):
                payload["admins"] = [payload["created_by"]]
            else:
                payload["admins"].append(payload["created_by"])

        # 3. Validate incoming data with Pydantic
        new_group = StudyGroup(**payload)

        # 4. Now get the client & db
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]

        # 5. Check if created_by is a valid user
        creator_id = new_group.created_by
        creator_user = User.find_by_id(creator_id)
        if not creator_user:
            return jsonify({"error": f"Creator user ID '{creator_id}' is invalid"}), 400

        # 6. Verify each admin is a valid user
        for admin_id in new_group.admins:
            admin_user = User.find_by_id(admin_id)
            if not admin_user:
                return jsonify({"error": f"Admin user ID '{admin_id}' is invalid"}), 400

        
        for member_id in new_group.members:
             member_user = User.find_by_id(member_id)
             if not member_user:
                return jsonify({"error": f"Member user ID '{member_id}' is invalid"}), 400

        # 7. Check for existing group with the same name
        existing = db["study_groups"].find_one({"name": new_group.name})
        if existing:
            return jsonify({"error": "A group with this name already exists."}), 400

        # 8. Insert the validated data into MongoDB
        group_doc = new_group.dict(by_alias=True)
        db["study_groups"].insert_one(group_doc)

        # 9. Return success
        return jsonify({
            "message": "Group created successfully",
            "group": new_group.dict()
        }), 201

    except ValidationError as ve:
        return jsonify({
            "error": "Validation failed",
            "details": ve.errors()
        }), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
