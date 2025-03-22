"""
This model represents an object that keeps track of the user's 
overarching educational goals and concerns.
"""

"""step 1: Import necessary modules"""
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, ClassVar
from services.azure_mongodb import MongoDBClient
from bson import ObjectId

"""Step 2: Define the UserJourney model"""
# Define the StudyPlan model
class EducationalPlan(BaseModel):
    chat_id: Optional[str] = None
    exercise: Optional[List[str]] = []
    submit_assignments: Optional[List[str]] = []
    assign_assignments: Optional[List[str]] = []
    assign_exercise: Optional[List[str]] = []
    share_resources: Optional[List[str]] = []

# Define the EducationalConcern model
class EducationalConcern(BaseModel):
    label: str
    severity: str

# Define the UserJourney model
class UserJourney(BaseModel):
    user_id: str
    student_goals: Optional[List[str]] = []
    last_update: Optional[datetime] = datetime.now()
    Study_plan: Optional[EducationalPlan] = None
    mental_health_concerns: Optional[List[EducationalConcern]] = []
    interested_subjects: Optional[List[str]] = []
    fieldOfStudy: Optional[str] = None
    
    def __init__(self, **data):
        if 'Study_plan' not in data or data['Study_plan'] is None:
            data['Study_plan'] = EducationalPlan()
        super().__init__(**data)
    
    @classmethod
    def create_from_user(cls, user):
        """Create a UserJourney instance from a User instance."""
        return cls(
            user_id=user.id,
            fieldOfStudy=user.fieldOfStudy,
            last_update=datetime.now()
        )
    
    @classmethod
    def find_by_user_id(cls, user_id):
        """Find a UserJourney by user_id."""
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        journey_data = db.user_journeys.find_one({"user_id": user_id})
        if journey_data:
            journey_data['id'] = str(journey_data.get('_id'))
            return cls(**journey_data)
        return None
    
    @classmethod
    def update_from_user(cls, user):
        """Update a UserJourney from a User instance."""
        journey = cls.find_by_user_id(user.id)
        if journey:
            db_client = MongoDBClient.get_client()
            db = db_client[MongoDBClient.get_db_name()]
            result = db.user_journeys.update_one(
                {"user_id": user.id},
                {"$set": {
                    "fieldOfStudy": user.fieldOfStudy,
                    "last_update": datetime.now()
                }}
            )
            return result.modified_count == 1
        else:
            # Create new journey if it doesn't exist
            new_journey = cls.create_from_user(user)
            # Code to save the new journey to the database would go here
            return True
    
    def save(self):
        """Save the UserJourney to the database."""
        db_client = MongoDBClient.get_client()
        db = db_client[MongoDBClient.get_db_name()]
        
        journey_dict = self.model_dump(exclude={"id"})
        
        if hasattr(self, 'id') and self.id:
            # Update existing record
            result = db.user_journeys.update_one(
                {"_id": ObjectId(self.id)},
                {"$set": journey_dict}
            )
            return result.modified_count == 1
        else:
            # Insert new record
            result = db.user_journeys.insert_one(journey_dict)
            self.id = str(result.inserted_id)
            return bool(result.inserted_id)