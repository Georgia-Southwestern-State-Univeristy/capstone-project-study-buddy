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
import traceback

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
                
            # Ensure liked_by exists
            if "liked_by" not in post:
                post["liked_by"] = []
            
            # Add user profile information
            user_id = post.get("user_id")
            if user_id in user_profiles:
                post["user_profile"] = user_profiles[user_id]
            else:
                post["user_profile"] = {
                    "username": "Unknown",
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