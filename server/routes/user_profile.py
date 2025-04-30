import json
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
    try:
        user_id = get_jwt_identity()
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]

        user_data = db['users'].find_one({"_id": ObjectId(user_id)})
        if user_data is None:
            return jsonify({"error": "User could not be found."}), 404

        # Convert MongoDB document to a regular dictionary
        user_dict = dict(user_data)
        
        # Remove sensitive information like passwords
        user_dict.pop('password', None)
        user_dict['_id'] = str(user_dict['_id'])

        # Fetch user_journey from DB
        user_journey_data = db['user_journeys'].find_one({"user_id": user_id})
        if user_journey_data:
            # Convert ObjectId to string to avoid circular reference errors
            user_journey_data['_id'] = str(user_journey_data['_id'])
            # Create a clean dictionary to avoid potential circular references
            user_journey_clean = dict(user_journey_data)
            user_dict['user_journey'] = user_journey_clean

        # Return the data as a clean dictionary
        return jsonify(user_dict), 200
    except Exception as e:
        current_app.logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({"error": f"An error occurred while retrieving the profile: {str(e)}"}), 500

# Update the user profile
@user_routes.patch('/user/profile')
@jwt_required()
def update_profile_fields():
    try:
        user_id = get_jwt_identity()
        # Handle both form data and JSON requests
        if request.is_json:
            update_fields = request.get_json()
        else:
            update_fields = request.form.to_dict() 
            
        if not update_fields:
            update_fields = {}
            
        files = request.files

        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]

        user = db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found."}), 404

        # Define which fields should ONLY go in user_journey
        journey_only_fields = ['mental_health_concerns', 'Study_plan', 'student_goals', 'interested_subjects']
        
        # Initialize containers for updates
        journey_updates = {}
        user_updates = {}
        
        # First, handle profile picture if provided
        if 'profile_picture' in files:
            profile_picture = files['profile_picture']
            if profile_picture.filename and allowed_file(profile_picture.filename):
                try:
                    blob_service = AzureBlobService()
                    old_pic_url = user.get('profile_picture')
                    if old_pic_url:
                        try:
                            blob_service.delete_blob(old_pic_url)
                        except Exception as e:
                            # Log error but continue with upload
                            current_app.logger.warning(f"Could not delete old profile picture: {str(e)}")
                    uniq_name = secure_filename(profile_picture.filename)
                    new_blob_url = blob_service.upload_file(profile_picture, uniq_name)
                    user_updates['profile_picture'] = new_blob_url
                except Exception as e:
                    return jsonify({"error": f"Error handling profile picture: {str(e)}"}), 400
            else:
                return jsonify({"error": "Invalid image format. Allowed formats: png, jpg, jpeg, gif"}), 400
        
        # Extract fieldOfStudy to update in both models
        field_of_study = update_fields.get('fieldOfStudy')
        if field_of_study:
            user_updates['fieldOfStudy'] = field_of_study
            journey_updates['fieldOfStudy'] = field_of_study
        
        # Process journey-specific fields
        for field in journey_only_fields:
            if field in update_fields:
                try:
                    # Try to parse JSON if it's a string
                    value = update_fields[field]
                    if isinstance(value, str):
                        journey_updates[field] = json.loads(value)
                    else:
                        journey_updates[field] = value
                except json.JSONDecodeError:
                    journey_updates[field] = []
        
        # Add remaining fields to user_updates
        for field, value in update_fields.items():
            if field not in journey_only_fields and field != 'fieldOfStudy':
                user_updates[field] = value
        
        # Update user document if there are user updates
        if user_updates:
            db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": user_updates})
        
        # Update user_journey document if there are journey updates
        if journey_updates:
            db["user_journeys"].update_one(
                {"user_id": user_id},
                {"$set": journey_updates},
                upsert=True
            )
        
        if not user_updates and not journey_updates:
            return jsonify({"message": "No fields to update."}), 200

        # Return updated profile picture URL if it was updated
        result = {"message": "Profile updated successfully"}
        if 'profile_picture' in user_updates:
            result['profile_picture'] = user_updates['profile_picture']
        
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error updating user profile: {str(e)}")
        return jsonify({"error": f"An error occurred while updating the profile: {str(e)}"}), 500


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
            return jsonify({"error": "User not found."}), 404

        # Delete profile picture from Azure Blob if it exists
        old_picture_url = user.get('profile_picture')
        if old_picture_url:
            try:
                blob_service = AzureBlobService()
                blob_service.delete_blob(old_picture_url)
            except Exception as e:
                # Log error but continue with deletion
                current_app.logger.warning(f"Could not delete profile picture: {str(e)}")

        # Delete the documents in the correct order: first user record then journey
        db["users"].delete_one({"_id": ObjectId(user_id)})
        db["user_journeys"].delete_one({"user_id": user_id})
        
        return jsonify({"message": "User has been deleted successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting user profile: {str(e)}")
        return jsonify({"error": "An error occurred while deleting the profile."}), 500
