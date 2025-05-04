from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from bson import ObjectId

# Custom field for handling ObjectId
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Base model for MongoDB documents with ID
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    
    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True

#--------------------------------------------------------------------------------------------------------------------------
# Message model
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now(tz=timezone.utc))

# Long-term memory model
class Memory(BaseModel):
    key_insights: List[str] = Field(default_factory=list)
    important_facts: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""

# Chat document model
class ChatDocument(MongoBaseModel):
    document_type: str = "chat"
    chat_id: str
    chat_name: str
    created_at: datetime = Field(default_factory=datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=datetime.now(tz=timezone.utc))
    messages: List[Message] = Field(default_factory=list)
    memory: Memory = Field(default_factory=Memory)

#--------------------------------------------------------------------------------------------------------------------------
# User preferences model
class UserPreferences(BaseModel):
    theme: str = "light"
    language: str = "en"
    notification_settings: Dict[str, bool] = Field(
        default_factory=lambda: {"email": True, "push": True}
    )

# User personal information model
class PersonalInfo(BaseModel):
    role: str
    location: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    education_level: Optional[str] = None
    timezone: Optional[str] = None
    # Add more fields as needed for your application

# User profile document model
class UserProfileDocument(MongoBaseModel):
    document_type: str = "profile"
    name: Optional[str] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    created_at: datetime = Field(default_factory=datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=datetime.now(tz=timezone.utc))

#--------------------------------------------------------------------------------------------------------------------------
# Create chat request model
class CreateChatRequest(BaseModel):
    chat_name: str

# Add message request model
class AddMessageRequest(BaseModel):
    role: str  # "user" or "assistant"
    content: str

# Update LTM request model
class UpdateMemoryRequest(BaseModel):
    key_insight: Optional[str] = None
    important_facts: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None

# Update profile request model
class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    preferences: Optional[UserPreferences] = None
    personal_info: Optional[PersonalInfo] = None

# User collection response model
class UserCollection(BaseModel):
    username: str
    collection_name: str

# Chat summary model (for listing chats)
class ChatSummary(BaseModel):
    chat_id: str
    chat_name: str
    created_at: datetime
    updated_at: datetime
    summary: Optional[str] = None  # From ltm.summary

# Response models
class ChatResponse(BaseModel):
    success: bool
    chat: Optional[ChatDocument] = None
    message: Optional[str] = None

class ProfileResponse(BaseModel):
    success: bool
    profile: Optional[UserProfileDocument] = None
    message: Optional[str] = None

class ChatsListResponse(BaseModel):
    success: bool
    chats: List[ChatSummary] = Field(default_factory=list)
    message: Optional[str] = None