from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from models.study_group import StudyGroup
from models.user import User  # <-- Import your User model
from services.azure_mongodb import MongoDBClient
from services.azure_blob_service import AzureBlobService
import json

import os
groups_routes = Blueprint("groups", __name__)

@groups_routes.route("/groups/create", methods=["POST"])
def create_group():
    try:
        # Check if the request has form data (for file uploads) or JSON
        has_form_data = request.content_type and 'multipart/form-data' in request.content_type
        
        if has_form_data:
            # 1. Extract form data fields
            payload = {}
            payload["name"] = request.form.get("name")
            payload["description"] = request.form.get("description", "")
            payload["privacy"] = request.form.get("privacy", "public")
            payload["created_by"] = request.form.get("created_by")
            
            # Handle arrays sent as JSON strings
            payload["topics"] = json.loads(request.form.get("topics", "[]"))
            payload["rules"] = json.loads(request.form.get("rules", "[]"))
            payload["members"] = json.loads(request.form.get("members", "[]"))
            
            # Handle image URL or file upload
            if "image_url" in request.form and request.form.get("image_url"):
                payload["image_url"] = request.form.get("image_url")
            elif "group_image" in request.files:
                # Upload the image file to Azure Blob Storage
                file = request.files["group_image"]
                blob_service = AzureBlobService.get_group_images_service()
                blob_url = blob_service.upload_file(file, file.filename)
                payload["image_url"] = blob_url
        else:
            # Get JSON payload for non-multipart requests
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


@groups_routes.route("/groups/join", methods=["POST"])
def join_group():
    """
    Join an existing study group by group_id (and optionally an invite code).
    Adds the user to the group's 'members' list if they're not already a member.
    """
    try:
        data = request.get_json(force=True)
        
        # 1. Extract necessary fields
        group_id = data.get("group_id")
        user_id = data.get("user_id")  # or get_jwt_identity() if using JWT

        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # 2. Validate that the user exists
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({"error": f"User with ID '{user_id}' does not exist"}), 400
        
        # 3. Connect to MongoDB
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]

        # 4. Find the group by its _id (using the string id)
        group = db["study_groups"].find_one({"_id": group_id})
        if not group:
            return jsonify({"error": f"Group with ID '{group_id}' does not exist"}), 404

        # 5. Check if user is already a member
        if user_id in group.get("members", []):
            return jsonify({"message": "User is already a member of this group"}), 200

        # 6. Add user to the group's 'members' list
        db["study_groups"].update_one(
            {"_id": group_id},
            {"$addToSet": {"members": user_id}}  # $addToSet prevents duplicates
        )

        return jsonify({
            "message": f"User {user_id} joined group {group_id} successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    


@groups_routes.route("/groups/retrieve", methods=["GET"])
def retrieve_groups():
    """
    Retrieve a list of study groups with optional pagination and filtering.
    
    Query Parameters:
      - page: (int) Page number (default is 1)
      - limit: (int) Number of groups per page (default is 10)
      - privacy: (str) Filter by privacy setting (e.g., 'public' or 'private')
      - name: (str) Partial name to search (case-insensitive)
      - topic: (str) Filter groups that include a specific topic
    """
    try:
        # 1. Connect to the database
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]
        
        # 2. Build the query filter from URL query parameters
        query = {}
        privacy = request.args.get("privacy")
        if privacy:
            query["privacy"] = privacy

        name = request.args.get("name")
        if name:
            # Use a case-insensitive regex for partial name matching
            query["name"] = {"$regex": name, "$options": "i"}
        
        topic = request.args.get("topic")
        if topic:
            # Find groups where the topics array contains the provided topic
            query["topics"] = {"$in": [topic]}
        
        # 3. Handle pagination: page & limit (default values provided)
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        skip = (page - 1) * limit
        
        # 4. Query the database for groups matching the filter
        groups_cursor = db["study_groups"].find(query).skip(skip).limit(limit)
        groups_list = list(groups_cursor)
        
        # 5. Optionally count total matching documents (for pagination metadata)
        total = db["study_groups"].count_documents(query)
        
        # 6. Convert each group document to a dict using the StudyGroup model 
        #    (this applies any json_encoders, e.g., ObjectId to str)
        groups = []
        for group_doc in groups_list:
            group = StudyGroup.parse_obj(group_doc)
            groups.append(group.dict())
        
        # 7. Return the list along with pagination metadata
        return jsonify({
            "message": "Groups retrieved successfully",
            "data": groups,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@groups_routes.route("/users/list", methods=["GET"])
def list_users():
    """
    Retrieve a list of users for dropdown selection.
    
    Query Parameters:
      - search: (str) Optional search string to filter users by username
    """
    try:
        # 1. Connect to the database
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]
        
        # 2. Build the query filter from URL query parameters
        query = {}
        search = request.args.get("search")
        if search:
            # Use a case-insensitive regex for partial username matching
            query["username"] = {"$regex": search, "$options": "i"}
        
        # 3. Query the database for users matching the filter
        # Project only necessary fields for dropdown (username, _id, profile_picture)
        users_cursor = db["users"].find(
            query, 
            {"_id": 1, "username": 1, "name": 1, "profile_picture": 1}
        ).limit(50)  # Limit to 50 results for performance
        
        users_list = []
        for user in users_cursor:
            users_list.append({
                "id": str(user["_id"]),
                "username": user["username"],
                "name": user.get("name", ""),
                "profile_picture": user.get("profile_picture", "")
            })
        
        return jsonify({
            "message": "Users retrieved successfully",
            "data": users_list
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500