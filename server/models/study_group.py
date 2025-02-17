from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class StudyGroup(BaseModel):
    id: str = Field(
        default_factory=lambda: str(ObjectId()),
        alias="_id",
        description="Unique identifier of the study group."
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="The name of the study group."
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="A brief description of the study group's focus and purpose."
    )
    topics: List[str] = Field(
        default_factory=list,
        description="A list of topics or subjects the group covers (e.g., Calculus, Literature)."
    )
    created_by: str = Field(
        ...,
        description="The user ID of the group creator."
    )
    admins: List[str] = Field(
        default_factory=list,
        description="User IDs of group administrators who can manage the group. The group creator should ideally be added here."
    )
    members: List[str] = Field(
        default_factory=list,
        description="User IDs of members participating in the group."
    )
    privacy: str = Field(
        "public",
        description="Privacy setting for the group. Valid options: 'public' or 'private'."
    )
    rules: List[str] = Field(
        default_factory=list,
        description="A list of rules or guidelines to maintain group decorum."
    )
    image_url: Optional[str] = Field(
        None,
        description="URL for the group's image or icon."
    )
    is_active: bool = Field(
        default=True,
        description="Indicator whether the group is active."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the group was created."
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last update to the group's information."
    )

    @validator('privacy')
    def validate_privacy(cls, v):
        allowed = {"public", "private"}
        if v not in allowed:
            raise ValueError("privacy must be either 'public' or 'private'")
        return v

    class Config:
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "611d1f1f1f1f1f1f1f1f1f1f",
                "name": "Calculus Study Group",
                "description": "A group dedicated to solving and discussing calculus problems.",
                "topics": ["Calculus", "Mathematics", "Differential Equations"],
                "created_by": "user_12345",
                "admins": ["user_12345", "user_67890"],
                "members": ["user_12345", "user_67890", "user_54321"],
                "privacy": "public",
                "rules": ["Respect others", "No spam", "Stay on topic"],
                "image_url": "https://example.com/group-icon.png",
                "is_active": True,
                "created_at": "2023-10-01T12:34:56Z",
                "updated_at": "2023-10-05T08:20:30Z"
            }
        }
