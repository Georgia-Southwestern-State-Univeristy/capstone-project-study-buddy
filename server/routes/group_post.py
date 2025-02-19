"""
This module defines HTTP and real-time WebSocket routes for handling 
group posts in study groups.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from flask_socketio import emit, join_room, leave_room
from bson import ObjectId
from datetime import datetime

from models.group_post import GroupPost
from models.user import User
from services.azure_mongodb import MongoDBClient
from utils.socketIo import socketio  

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
        if not post_id:
            return emit("error", {"message": "Missing post_id"})

        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]

        db["group_posts"].update_one({"_id": ObjectId(post_id)}, {"$inc": {"likes": 1}})

        emit("post_liked", {"post_id": post_id}, broadcast=True)

    except Exception as e:
        emit("error", {"message": str(e)})

@socketio.on("comment_post")
def handle_comment_post(data):
    """
    Handles real-time comments on posts.
    """
    try:
        post_id = data.get("post_id")
        comment = data.get("comment")

        if not post_id or not comment:
            return emit("error", {"message": "Missing post_id or comment"})

        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        db["group_posts"].update_one({"_id": ObjectId(post_id)}, {"$inc": {"comments": 1}})

        emit("post_commented", {"post_id": post_id, "comment": comment}, broadcast=True)

    except Exception as e:
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

        socketio.emit("new_group_post", new_post.dict(), room=f"group_{new_post.group_id}")

        return jsonify({"message": "Post created successfully", "post": new_post.dict()}), 201

    except ValidationError as ve:
        return jsonify({"error": "Validation failed", "details": ve.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@group_posts_routes.route("/group_posts/<group_id>", methods=["GET"])
def get_group_posts(group_id):
    """
    Retrieves all posts for a given group.
    """
    try:
        client = MongoDBClient.get_client()
        db = client[MongoDBClient.get_db_name()]
        posts = list(db["group_posts"].find({"group_id": group_id}))

        return jsonify({"message": "Posts retrieved successfully", "data": posts}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
