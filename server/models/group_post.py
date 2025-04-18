from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class Comment(BaseModel):
    user_id: str = Field(
        ...,
        description="The user ID of the person who wrote the comment."
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Text content of the comment."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the comment was created."
    )

class GroupPost(BaseModel):
    id: str = Field(
        default_factory=lambda: str(ObjectId()),
        alias="_id",
        description="Unique identifier for the post."
    )
    group_id: str = Field(
        ...,
        description="The study group's ID to which this post belongs."
    )
    user_id: str = Field(
        ...,
        description="The user ID of the person who created the post."
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Text content of the post."
    )
    attachments: List[str] = Field(
        default_factory=list,
        description="List of URLs for any attachments (images, documents, etc.)."
    )
    likes: int = Field(
        default=0,
        description="The number of likes the post has received."
    )
    liked_by: List[str] = Field(
        default_factory=list,
        description="List of user IDs who have liked this post."
    )
    comments: int = Field(
        default=0,
        description="The number of comments on the post."
    )
    comment_list: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of comments on this post."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the post was created."
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last update to the post."
    )

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }
        schema_extra = {
            "example": {
                "_id": "611d2a2a2a2a2a2a2a2a2a",
                "group_id": "611d1f1f1f1f1f1f1f1f1f1f",
                "user_id": "user_67890",
                "content": "Does anyone have tips on solving integrals using substitution?",
                "attachments": [],
                "likes": 5,
                "liked_by": ["user_12345", "user_67890", "user_24680"],
                "comments": 2,
                "comment_list": [
                    {
                        "user_id": "user_12345",
                        "content": "I found using U-substitution really helpful!",
                        "created_at": "2023-10-02T15:30:00Z"
                    },
                    {
                        "user_id": "user_24680",
                        "content": "Check out Khan Academy's videos on integration techniques.",
                        "created_at": "2023-10-02T16:15:00Z"
                    }
                ],
                "created_at": "2023-10-02T15:00:00Z",
                "updated_at": "2023-10-02T16:00:00Z"
            }
        }
