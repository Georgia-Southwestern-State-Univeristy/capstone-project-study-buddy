"""
This module defines the Resume model and associated sub-models,
which represent a user's resume in the system.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from bson import ObjectId
from services.azure_mongodb import MongoDBClient

# -----------------------------
# Sub-models for repeated fields
# -----------------------------
class SocialAccount(BaseModel):
    platform: Optional[str] = Field(None, description="e.g. LinkedIn, Twitter")
    handle: Optional[str] = Field(None, description="e.g. @john_doe")
    link:   Optional[str] = Field(None, description="Full URL to the profile")


class EducationItem(BaseModel):
    school: Optional[str] = None
    grad:   Optional[str] = None  # e.g. "2025-05" or "May 2025"
    major:  Optional[str] = None


class ExperienceItem(BaseModel):
    exp_company:      Optional[str] = None
    exp_date:         Optional[str] = None  # e.g. "2021 - 2023"
    exp_description:  Optional[str] = None


class ProjectItem(BaseModel):
    projectName: Optional[str] = None
    projectUrl:  Optional[str] = None
    projectDesc: Optional[str] = None


class ReferenceItem(BaseModel):
    refName:    Optional[str] = None
    refContact: Optional[str] = None  # e.g. "jane@somecompany.com"


# ---------------------------------
# Main Resume model
# ---------------------------------
class Resume(BaseModel):
    """
    The Resume model defines the structure of a user's resume,
    including personal info, career goals, contact info, and
    dynamic arrays (education, experience, etc.).
    """
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="Reference to the associated User._id")

    # Personal / Career
    fName: Optional[str] = None
    lName: Optional[str] = None
    description: Optional[str] = None
    career: Optional[str] = None
    career2: Optional[str] = None
    career3: Optional[str] = None

    # Contact
    phoneNum: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    socialAccounts: List[SocialAccount] = Field(default_factory=list)

    # Skills / Achievements
    skills: Optional[str] = None
    achievements: Optional[str] = None
    certifications: Optional[str] = None

    # Repeated fields
    education: List[EducationItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    references: List[ReferenceItem] = Field(default_factory=list)

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # -----------------------------------------
    # Class methods to interface with MongoDB
    # -----------------------------------------
    def save(self):
        """
        Insert or update the resume document in the 'resumes' collection.
        If self.id is present, we update; otherwise we insert a new document.
        """
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        resumes_coll = db.resumes

        # Set timestamps
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now

        # Convert to dict
        resume_dict = self.dict(by_alias=True, exclude_unset=True)

        if self.id:
            # Update existing doc
            object_id = ObjectId(self.id)
            resumes_coll.update_one({"_id": object_id}, {"$set": resume_dict})
        else:
            # Insert new doc
            result = resumes_coll.insert_one(resume_dict)
            self.id = str(result.inserted_id)

    @classmethod
    def find_by_id(cls, resume_id: str):
        """
        Retrieve a resume by its _id from the 'resumes' collection.
        """
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        resumes_coll = db.resumes

        data = resumes_coll.find_one({"_id": ObjectId(resume_id)})
        if data:
            data["id"] = str(data["_id"])
            return cls(**data)
        return None

    @classmethod
    def find_by_user_id(cls, user_id: str):
        """
        Retrieve the resume(s) for a given user_id.
        Potentially returns multiple if a user can have multiple resumes.
        """
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        resumes_coll = db.resumes

        cursor = resumes_coll.find({"user_id": user_id})
        results = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            results.append(cls(**doc))
        return results

    @classmethod
    def delete_by_id(cls, resume_id: str):
        """
        Delete a resume by its _id.
        """
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        resumes_coll = db.resumes
        result = resumes_coll.delete_one({"_id": ObjectId(resume_id)})
        return result.deleted_count == 1
