"""
This module defines HTTP and real-time WebSocket routes for handling 
group posts in study groups.
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from pydantic import ValidationError
from flask_socketio import emit, join_room, leave_room
from bson import ObjectId
from models.group_post import GroupPost
from models.user import User
from services.azure_mongodb import MongoDBClient
from utils.socketIo import socketio  
from datetime import datetime
import traceback
from services.azure_blob_service import AzureBlobService

group_posts_routes = Blueprint("group_posts", __name__)


# --------------------------------
# 🔹 SOCKET.IO EVENT HANDLERS
# --------------------------------

@socketio.on("join_group_room")
def handle_join_group_room(data):
    """
    Allows a user to join a study group's real-time chat room.
    Expected data:
    {
        "group_id": "<group_id>",
        "user_id": "<user_id>"
    }
    """
    try:
        group_id = data.get("group_id")
        user_id = data.get("user_id")

        if not group_id or not user_id:
            return emit("error", {"message": "Missing group_id or user_id"}, to=request.sid)

        room_name = f"group_{group_id}"
        join_room(room_name)

        emit("group_notification", {
            "message": f"User {user_id} joined group {group_id}",
            "group_id": group_id,
            "user_id": user_id
        }, room=room_name)

    except Exception as e:
        emit("error", {"message": str(e)})

@socketio.on("leave_group_room")
def handle_leave_group_room(data):
    """
    Allows a user to leave a study group's real-time chat room.
    """
    try:
        group_id = data.get("group_id")
        user_id = data.get("user_id")

        if not group_id or not user_id:
            return emit("error", {"message": "Missing group_id or user_id"}, to=request.sid)

        room_name = f"group_{group_id}"
        leave_room(room_name)

        emit("group_notification", {
            "message": f"User {user_id} left group {group_id}",
            "group_id": group_id,
            "user_id": user_id
        }, room=room_name)

    except Exception as e:
        emit("error", {"message": str(e)})



@socketio.on("toggle_like_post")
def handle_toggle_like_post(data):
    """
    Handles toggling post likes (like/unlike).
    Expected data:
    {
        "post_id": "<post_id>",
        "user_id": "<user_id>",
        "is_liking": true|false  # optional - used as a hint but we'll check the actual state
    }
    """
    try:
        post_id = data.get("post_id")
        user_id = data.get("user_id")
        
        print(f"Toggle like request received for post ID: {post_id} by user: {user_id}")
        
        if not post_id or not user_id:
            print("Missing post_id or user_id in toggle_like_post data")
            return emit("error", {"message": "Missing post_id or user_id"})

        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]

        # Try multiple approaches to find the post
        post = None
        post_db_id = None
        
        # First try: direct string match (in case _id is stored as string)
        post = db["group_posts"].find_one({"_id": post_id})
        if post:
            post_db_id = post["_id"]
            print(f"Found post with string ID: {post_id}")
        
        # Second try: ObjectId conversion
        if not post:
            try:
                post_obj_id = ObjectId(post_id)
                post = db["group_posts"].find_one({"_id": post_obj_id})
                if post:
                    post_db_id = post["_id"]
                    print(f"Found post with ObjectId: {post_obj_id}")
            except Exception as e:
                print(f"Error converting to ObjectId: {str(e)}")
        
        # Debug: List some posts from the collection
        if not post:
            print("Post not found. Checking collection for sample posts...")
            sample_posts = list(db["group_posts"].find().limit(3))
            if sample_posts:
                print(f"Sample post IDs in collection: {[str(p.get('_id')) for p in sample_posts]}")
                print(f"Sample post types: {[type(p.get('_id')).__name__ for p in sample_posts]}")
            else:
                print("No posts found in collection")
            
            return emit("error", {"message": f"Post with ID {post_id} not found in database"})
        
        # Check if user has already liked this post
        already_liked = False
        if "liked_by" in post and post["liked_by"] is not None:
            already_liked = user_id in post["liked_by"]
        
        print(f"User {user_id} already liked post: {already_liked}")
        
        if already_liked:
            # User already liked the post, so unlike it
            result = db["group_posts"].update_one(
                {"_id": post_db_id}, 
                {
                    "$pull": {"liked_by": user_id},
                    "$inc": {"likes": -1}
                }
            )
            
            print(f"Unlike operation result: {result.modified_count} document(s) modified")
            
            if result.modified_count == 0:
                print(f"Failed to unlike post {post_id}")
                # Try a find_and_modify approach as alternative
                updated_post = db["group_posts"].find_one_and_update(
                    {"_id": post_db_id},
                    {
                        "$pull": {"liked_by": user_id},
                        "$inc": {"likes": -1}
                    },
                    return_document=True  # Return the updated document
                )
                
                if not updated_post:
                    return emit("error", {"message": f"Failed to unlike post {post_id}"})
                likes_count = updated_post.get("likes", 0)
            else:
                # Get updated post
                updated_post = db["group_posts"].find_one({"_id": post_db_id})
                likes_count = updated_post.get("likes", 0)
            
            print(f"Post {post_id} unliked by {user_id}. New count: {likes_count}")
            
            # Emit unlike event
            emit("post_unliked", {
                "post_id": post_id, 
                "user_id": user_id,
                "likes": likes_count
            }, broadcast=True)
            
        else:
            # Initialize liked_by if it doesn't exist
            if "liked_by" not in post or post["liked_by"] is None:
                db["group_posts"].update_one(
                    {"_id": post_db_id},
                    {"$set": {"liked_by": []}}
                )
            
            # User hasn't liked the post yet, so like it
            result = db["group_posts"].update_one(
                {"_id": post_db_id}, 
                {
                    "$addToSet": {"liked_by": user_id},
                    "$inc": {"likes": 1}
                }
            )
            
            print(f"Like operation result: {result.modified_count} document(s) modified")
            
            if result.modified_count == 0:
                print(f"Failed to like post {post_id}")
                # Try a find_and_modify approach as alternative
                updated_post = db["group_posts"].find_one_and_update(
                    {"_id": post_db_id},
                    {
                        "$addToSet": {"liked_by": user_id},
                        "$inc": {"likes": 1}
                    },
                    return_document=True  # Return the updated document
                )
                
                if not updated_post:
                    return emit("error", {"message": f"Failed to like post {post_id}"})
                likes_count = updated_post.get("likes", 0)
            else:
                # Get updated post
                updated_post = db["group_posts"].find_one({"_id": post_db_id})
                likes_count = updated_post.get("likes", 0)
            
            print(f"Post {post_id} liked by {user_id}. New count: {likes_count}")
            
            # Emit like event
            emit("post_liked", {
                "post_id": post_id, 
                "user_id": user_id,
                "likes": likes_count
            }, broadcast=True)
            
    except Exception as e:
        print(f"Error in toggle_like_post: {str(e)}")
        print(traceback.format_exc())
        emit("error", {"message": str(e)})


@socketio.on("comment_post")
def handle_comment_post(data):
    """
    Handles real-time comments on posts.
    """
    try:
        post_id = data.get("post_id")
        comment = data.get("comment")
        user_id = data.get("user_id", "Anonymous")
        
        print(f"Comment request received for post ID: {post_id}")

        if not post_id or not comment:
            print("Missing post_id or comment in comment_post data")
            return emit("error", {"message": "Missing post_id or comment"})

        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        
        # Convert post_id to ObjectId and ensure it's valid
        try:
            post_obj_id = ObjectId(post_id)
        except Exception as e:
            print(f"Invalid post_id format: {post_id}, error: {str(e)}")
            return emit("error", {"message": f"Invalid post_id format: {str(e)}"})

        # First check if the post exists
        post = db["group_posts"].find_one({"_id": post_obj_id})
        if not post:
            # Try to find by string ID as a fallback - ADD THIS PART
            print(f"Post not found by ObjectId, trying string ID")
            post = db["group_posts"].find_one({"_id": post_id})
            if not post:
                print(f"Post with ID {post_id} not found in database")
                # List all posts in the collection for debugging
                all_posts = list(db["group_posts"].find({}, {"_id": 1}))
                print(f"Available post IDs: {[str(p['_id']) for p in all_posts]}")
                return emit("error", {"message": f"Post with ID {post_id} not found"})
            else:
                # If found by string ID, use that
                post_obj_id = post_id
        
        # Create a comment object
        comment_obj = {
            "user_id": user_id,
            "content": comment,
            "created_at": datetime.utcnow()
        }
        
        # Initialize comment_list field if it doesn't exist
        if "comment_list" not in post:
            db["group_posts"].update_one(
                {"_id": post_obj_id},
                {"$set": {"comment_list": []}}
            )
        
        # Add comment to comments array and increment counter
        result = db["group_posts"].update_one(
            {"_id": post_obj_id}, 
            {
                "$push": {"comment_list": comment_obj},
                "$inc": {"comments": 1}
            }
        )

        if result.modified_count == 0:
            print(f"Failed to add comment to post {post_id}")
            return emit("error", {"message": f"Failed to add comment to post {post_id}"})

        # Get updated comment count
        updated_post = db["group_posts"].find_one({"_id": post_obj_id})
        comment_count = updated_post.get("comments", 0)
        print(f"Comment added to post {post_id}. New comment count: {comment_count}")

        emit("post_commented", {
            "post_id": post_id, 
            "comment": comment,
            "user_id": user_id,
            "comments": comment_count
        }, broadcast=True)

    except Exception as e:
        import traceback
        print(f"Error in comment_post: {str(e)}")
        print(traceback.format_exc())
        emit("error", {"message": str(e)})

# --------------------------------
# 🔹 HTTP ROUTES
# --------------------------------

@group_posts_routes.route("/group_posts", methods=["POST"])
def create_group_post():
    """
    Creates a new group post and broadcasts it in real-time.
    """
    try:
        # Check if the request has files
        files = []
        if 'files[]' in request.files:
            uploaded_files = request.files.getlist('files[]')
            
            # Initialize Azure Blob Service for post attachments
            blob_service = AzureBlobService(container_name="post-attachments")
            
            # Upload each file and collect URLs
            for file in uploaded_files:
                if file and file.filename:
                    # Create a unique filename with timestamp
                    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                    blob_url = blob_service.upload_file(file, filename)
                    files.append(blob_url)
        
        # Get form data or JSON data depending on content type
        if request.files:
            # If files were uploaded, other data is in form fields
            post_data = {
                "user_id": request.form.get("user_id"),
                "group_id": request.form.get("group_id"),
                "content": request.form.get("content"),
                "attachments": files
            }
        else:
            # Otherwise, it's just JSON data
            post_data = request.get_json(force=True)
            
        # Create new post with the data
        new_post = GroupPost(**post_data)

        user = User.find_by_id(new_post.user_id)
        if not user:
            return jsonify({"error": "Invalid user_id. User does not exist"}), 400

        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]
        post_doc = new_post.dict(by_alias=True)
        db["group_posts"].insert_one(post_doc)

        # Fix: Remove json_encoders parameter and use model_dump instead of dict if using Pydantic v2
        # For Pydantic v1, just remove the json_encoders parameter
        try:
            # First attempt with model_dump for Pydantic v2
            post_data = new_post.model_dump(by_alias=True, exclude_none=True)
        except AttributeError:
            # Fallback to dict for Pydantic v1
            post_data = new_post.dict(by_alias=True, exclude_none=True)
            
        # Convert datetime objects manually if needed
        if isinstance(post_data.get("created_at"), datetime):
            post_data["created_at"] = post_data["created_at"].isoformat()
        if isinstance(post_data.get("updated_at"), datetime):
            post_data["updated_at"] = post_data["updated_at"].isoformat()

        socketio.emit(
            "new_group_post",
            post_data,
            room=f"group_{new_post.group_id}"
        )

        return jsonify({"message": "Post created successfully", "post": new_post.dict()}), 201

    except ValidationError as ve:
        return jsonify({"error": "Validation failed", "details": ve.errors()}), 400
    except Exception as e:
        print(f"Error in create_group_post: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@group_posts_routes.route("/group_posts/<group_id>", methods=["GET"])
def get_group_posts(group_id):
    """
    Retrieves all posts for a given group.
    """
    try:
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]
        
        print(f"Fetching posts for group: {group_id}")
        
        # Fetch posts for this group
        posts = list(db["group_posts"].find({"group_id": group_id}))
        print(f"Found {len(posts)} posts for group {group_id}")
        
        # Collect unique user IDs from posts
        user_ids = set()
        for post in posts:
            user_ids.add(post.get("user_id"))
        
        # Fetch user profiles in one query
        user_profiles = {}
        if user_ids:
            users_data = list(db["users"].find({"_id": {"$in": [ObjectId(uid) for uid in user_ids if uid]}}))
            for user in users_data:
                user_id = str(user.get("_id"))
                user_profiles[user_id] = {
                    "username": user.get("username", "Anonymous"),
                    "name": user.get("name", ""),
                    "profile_picture": user.get("profile_picture", "")
                }
        
        # Process each post
        for post in posts:
            # Make sure ID is a string
            if isinstance(post.get("_id"), ObjectId):
                post["_id"] = str(post["_id"])
            
            # Ensure required fields exist
            if "likes" not in post or post["likes"] is None:
                post["likes"] = 0
            
            if "comments" not in post or post["comments"] is None:
                post["comments"] = 0
                
            if "comment_list" not in post:
                post["comment_list"] = []
                
            # Ensure liked_by exists
            if "liked_by" not in post:
                post["liked_by"] = []
            
            # Add user profile information
            user_id = post.get("user_id")
            if user_id in user_profiles:
                post["user_profile"] = user_profiles[user_id]
            else:
                post["user_profile"] = {
                    "username": "Anonymous",
                    "name": "",
                    "profile_picture": ""
                }
        
        return jsonify({
            "message": "Posts retrieved successfully", 
            "data": posts
        }), 200

    except Exception as e:
        print(f"Error retrieving posts: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# Modify the existing route to explicitly print the post_id
@group_posts_routes.route("/group_posts/<post_id>", methods=["DELETE"])
def delete_group_post(post_id):
    """
    Deletes a group post. Only the creator of the post can delete it.
    """
    try:
        print(f"DELETE request received for post_id: {post_id}")
        # Get the user_id from request
        request_data = request.get_json(force=True)
        user_id = request_data.get("user_id")
        print(f"Received user_id: {user_id}")
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]
        
        # Try to find the post - add more debugging
        post = None
        post_db_id = None
        
        print(f"Searching for post with ID: {post_id}")
        
        # First try with ObjectId
        try:
            post_obj_id = ObjectId(post_id)
            post = db["group_posts"].find_one({"_id": post_obj_id})
            if post:
                post_db_id = post_obj_id
                print(f"Found post with ObjectId: {post_id}")
        except Exception as e:
            print(f"Error converting to ObjectId: {str(e)}")
            
        # Fallback to string ID if needed
        if not post:
            try:
                post = db["group_posts"].find_one({"_id": post_id})
                if post:
                    post_db_id = post_id
                    print(f"Found post with string ID: {post_id}")
            except Exception as e:
                print(f"Error finding post with string ID: {str(e)}")
                
        if not post:
            print(f"Post not found with ID: {post_id}")
            return jsonify({"error": "Post not found"}), 404
            
        # Check if the user is the creator of the post
        if post.get("user_id") != user_id:
            return jsonify({"error": "Unauthorized. Only the creator can delete this post"}), 403
            
        # Get the group_id before deleting the post (for notification)
        group_id = post.get("group_id")
        
        # Delete the post
        print(f"Attempting to delete post with _id: {post_db_id}")
        result = db["group_posts"].delete_one({"_id": post_db_id})
        
        if result.deleted_count == 0:
            print(f"Delete operation failed, deleted_count: 0")
            return jsonify({"error": "Failed to delete post"}), 500
            
        print(f"Post deleted successfully, deleted_count: {result.deleted_count}")
            
        # Notify users in the group about the deletion
        socketio.emit(
            "post_deleted",
            {"post_id": post_id, "user_id": user_id},
            room=f"group_{group_id}"
        )
        
        return jsonify({"message": "Post deleted successfully"}), 200
        
    except Exception as e:
        print(f"Error in delete_group_post: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@group_posts_routes.route("/group_posts/<post_id>", methods=["PUT"])
def edit_group_post(post_id):
    """
    Edits a group post. Only the creator of the post can edit it.
    Supports updating content and attachments (adding new ones and removing existing ones).
    """
    try:
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]
        
        # Check if the post exists
        post = None
        post_db_id = None
        
        print(f"Searching for post with ID: {post_id}")
        
        # First try with ObjectId
        try:
            post_obj_id = ObjectId(post_id)
            post = db["group_posts"].find_one({"_id": post_obj_id})
            if post:
                post_db_id = post_obj_id
                print(f"Found post with ObjectId: {post_id}")
        except Exception as e:
            print(f"Error converting to ObjectId: {str(e)}")
            
        # Fallback to string ID if needed
        if not post:
            try:
                post = db["group_posts"].find_one({"_id": post_id})
                if post:
                    post_db_id = post_id
                    print(f"Found post with string ID: {post_id}")
            except Exception as e:
                print(f"Error finding post with string ID: {str(e)}")
                
        if not post:
            print(f"Post not found with ID: {post_id}")
            return jsonify({"error": "Post not found"}), 404
        
        # Handle different request types (FormData or JSON)
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            # FormData request
            user_id = request.form.get("user_id")
            content = request.form.get("content")
            keep_attachments_json = request.form.get("keep_attachments")
            deleted_attachments_json = request.form.get("deleted_attachments")
            
            if not user_id or not content:
                return jsonify({"error": "User ID and content are required"}), 400
            
            # Check if the user is authorized to edit
            if post.get("user_id") != user_id:
                return jsonify({"error": "Unauthorized. Only the creator can edit this post"}), 403
            
            # Process attachments
            current_attachments = post.get("attachments", [])
            
            # Process attachments to keep
            keep_attachments = []
            if keep_attachments_json:
                import json
                try:
                    keep_attachments = json.loads(keep_attachments_json)
                except Exception as e:
                    print(f"Error parsing keep_attachments JSON: {str(e)}")
            
            # Process deleted attachments
            deleted_attachments = []
            if deleted_attachments_json:
                import json
                try:
                    deleted_attachments = json.loads(deleted_attachments_json)
                    # Delete blobs from storage
                    try:
                        blob_service = AzureBlobService(container_name="post-attachments")
                        for url in deleted_attachments:
                            blob_service.delete_blob(url)
                    except Exception as e:
                        print(f"Warning: Could not delete blobs: {str(e)}")
                except Exception as e:
                    print(f"Error parsing deleted_attachments JSON: {str(e)}")
            
            # If keep_attachments is provided, use it as the base
            # Otherwise, keep all attachments that aren't in deleted_attachments
            final_attachments = []
            if keep_attachments:
                final_attachments = keep_attachments
            else:
                final_attachments = [url for url in current_attachments if url not in deleted_attachments]
            
            # Process new file uploads
            new_files = []
            if 'files[]' in request.files:
                uploaded_files = request.files.getlist('files[]')
                
                # Initialize Azure Blob Service for post attachments
                blob_service = AzureBlobService(container_name="post-attachments")
                
                # Upload each file and collect URLs
                for file in uploaded_files:
                    if file and file.filename:
                        # Create a unique filename with timestamp
                        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                        try:
                            blob_url = blob_service.upload_file(file, filename)
                            new_files.append(blob_url)
                        except Exception as e:
                            print(f"Error uploading file {filename}: {str(e)}")
            
            # Combine kept attachments and new files
            updated_attachments = final_attachments + new_files
            
            # Update the post
            result = db["group_posts"].update_one(
                {"_id": post_db_id},
                {
                    "$set": {
                        "content": content,
                        "attachments": updated_attachments,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
        else:
            # JSON request for simple content update
            request_data = request.get_json(force=True)
            user_id = request_data.get("user_id")
            content = request_data.get("content")
            
            if not user_id or not content:
                return jsonify({"error": "User ID and content are required"}), 400
                
            # Check if the user is the creator of the post
            if post.get("user_id") != user_id:
                return jsonify({"error": "Unauthorized. Only the creator can edit this post"}), 403
                
            # Update the post with new content and updated timestamp
            result = db["group_posts"].update_one(
                {"_id": post_db_id},
                {
                    "$set": {
                        "content": content,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
        if result.modified_count == 0:
            return jsonify({"error": "Failed to update post"}), 500
            
        # Get the updated post
        updated_post = db["group_posts"].find_one({"_id": post_db_id})
        
        # Ensure the updated_at field is serializable
        if isinstance(updated_post.get("updated_at"), datetime):
            updated_post["updated_at"] = updated_post["updated_at"].isoformat()
            
        # Ensure the _id field is a string
        if isinstance(updated_post.get("_id"), ObjectId):
            updated_post["_id"] = str(updated_post["_id"])
            
        # Notify users in the group about the edit
        socketio.emit(
            "post_updated",
            {
                "post_id": post_id,
                "user_id": user_id,
                "content": content,
                "updated_at": updated_post.get("updated_at"),
                "attachments": updated_post.get("attachments", [])
            },
            room=f"group_{post.get('group_id')}"
        )
        
        return jsonify({
            "message": "Post updated successfully",
            "post": updated_post
        }), 200
        
    except Exception as e:
        print(f"Error in edit_group_post: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500