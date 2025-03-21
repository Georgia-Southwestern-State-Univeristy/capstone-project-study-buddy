from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename

from services.azure_mongodb import MongoDBClient
from services.azure_blob_service import AzureBlobService  # <-- import our blob service

user_routes = Blueprint('user_routes', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Get the user profile
@user_routes.get('/user/profile')
@jwt_required()
def get_public_profile():
    user_id = get_jwt_identity()
    db_client = MongoDBClient.get_client()
    db = db_client[MongoDBClient.get_db_name()]

    user_data = db['users'].find_one({"_id": ObjectId(user_id)})
    if user_data is None:
        return jsonify({"error": "User could not be found."}), 404

    # Remove sensitive information like passwords
    user_data.pop('password', None)
    
    # Convert _id from ObjectId to string if needed
    user_data['_id'] = str(user_data['_id'])
    print('user_data:', user_data)
    return jsonify(user_data), 200

# Update the user profile
@user_routes.patch('/user/profile')
@jwt_required()
def update_profile_fields():
    try:
        user_id = get_jwt_identity()
        update_fields = request.form.to_dict()
        files = request.files

        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        user = db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User cannot be found."}), 404

        # Initialize Azure Blob Service
        blob_service = AzureBlobService()

        # Handle profile picture update
        if 'profile_picture' in files:
            profile_picture = files['profile_picture']
            if profile_picture.filename != '' and allowed_file(profile_picture.filename):
                # 1) Delete old profile picture from Azure, if it exists
                old_picture_url = user.get('profile_picture')
                if old_picture_url:
                    blob_service.delete_blob(old_picture_url)

                # 2) Upload new profile picture to Azure
                filename = secure_filename(profile_picture.filename)
                unique_filename = f"{user['username']}_{filename}"
                new_blob_url = blob_service.upload_file(profile_picture, unique_filename)

                # 3) Update the user's profile_picture field
                update_fields['profile_picture'] = new_blob_url
            else:
                return jsonify({"error": "Invalid image format"}), 400

        # Update other fields (like name, age, etc.) if provided
        if update_fields:
            db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})
            return jsonify({
                "message": "User has been updated successfully.",
                "profile_picture": update_fields.get('profile_picture', user.get('profile_picture'))
            }), 200
        else:
            return jsonify({"message": "No fields to update."}), 200

    except Exception as e:
        current_app.logger.error(f"Error updating user profile: {str(e)}")
        return jsonify({"error": "An error occurred while updating the profile"}), 500

# Delete the user profile
@user_routes.delete('/user/profile')
@jwt_required()
def delete_profile():
    try:
        user_id = get_jwt_identity()
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        
        user = db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User cannot be found."}), 404

        # Delete profile picture from Azure Blob if it exists
        old_picture_url = user.get('profile_picture')
        if old_picture_url:
            blob_service = AzureBlobService()
            blob_service.delete_blob(old_picture_url)

        # Now remove user from Mongo
        db["users"].delete_one({"_id": ObjectId(user_id)})
        
        return jsonify({"message": "User has been deleted successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting user profile: {str(e)}")
        return jsonify({"error": "An error occurred while deleting the profile."}), 500
