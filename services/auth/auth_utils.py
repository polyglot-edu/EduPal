from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId

# Models
class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = "student"  # defaults to "student" if not provided

class User(BaseModel):
    id: str
    username: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Invalid authentication scheme."
                )
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Invalid authorization code."
            )


#--------------------------------------------------------------------------------------------------------------------------
class UserPreferences(BaseModel):
    theme: str = "light"
    language: str = "en"
    notification_settings: Dict[str, bool] = Field(
        default_factory=lambda: {"email": True, "push": True}
    )
    email: str = ""

class PersonalInfo(BaseModel):
    role: str
    name: Optional[str]
    age: Optional[int]
    location: Optional[str]
    interests: Optional[List[str]]
    education_level: Optional[str]

    def to_str(self) -> str:
        return "\n".join([f"{k}: {v}" for k, v in self.model_dump().items()
                         if v is not None and v != [] and v != ""])

class UserProfileDocument(BaseModel):
    document_type: str = "profile"
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    personal_info: PersonalInfo
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
