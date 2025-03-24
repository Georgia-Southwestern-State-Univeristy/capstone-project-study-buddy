"""
This module defines HTTP and real-time WebSocket routes for handling 
group posts in study groups.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from flask_socketio import emit, join_room, leave_room
from bson import ObjectId
from models.group_post import GroupPost
from models.user import User
from services.azure_mongodb import MongoDBClient
from utils.socketIo import socketio  
from datetime import datetime

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

@socketio.on("like_post")
def handle_like_post(data):
    """
    Handles real-time post likes.
    """
    try:
        post_id = data.get("post_id")
        print(f"Like request received for post ID: {post_id}")
        
        if not post_id:
            print("Missing post_id in like_post data")
            return emit("error", {"message": "Missing post_id"})

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
            # Try to find by string ID as a fallback
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

        # Update likes count with upsert=True to ensure field exists
        result = db["group_posts"].update_one(
            {"_id": post_obj_id}, 
            {"$inc": {"likes": 1}},
            upsert=True
        )

        if result.modified_count == 0 and result.upserted_id is None:
            print(f"Failed to update likes for post {post_id}")
            return emit("error", {"message": f"Failed to update likes for post {post_id}"})

        # Get updated post to confirm likes count
        updated_post = db["group_posts"].find_one({"_id": post_obj_id})
        likes_count = updated_post.get("likes", 0)
        print(f"Post {post_id} liked successfully. New count: {likes_count}")

        emit("post_liked", {"post_id": post_id, "likes": likes_count}, broadcast=True)

    except Exception as e:
        import traceback
        print(f"Error in like_post: {str(e)}")
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
        data = request.get_json(force=True)
        new_post = GroupPost(**data)

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
            
            print(f"Post ID: {post['_id']}, User: {post.get('user_profile', {}).get('username', 'Unknown')}, Likes: {post['likes']}, Comments: {post['comments']}")
        
        return jsonify({
            "message": "Posts retrieved successfully", 
            "data": posts
        }), 200

    except Exception as e:
        import traceback
        print(f"Error retrieving posts: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500