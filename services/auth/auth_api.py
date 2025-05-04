from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import os
from .auth_utils import UserCreate, User, Token
from .auth_service import get_password_hash, authenticate_user, create_access_token, get_current_user, get_next_user_number, decode_token, verify_password, invalidate_token

# Constants
SECRET_KEY = os.getenv("USERS_SECRET_KEY", "")
ALGORITHM = "HS256"
EXP_TIME = 90  # Token expiration in days
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # MongoDB URI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

# MongoDB connection
client = MongoClient(MONGO_URI)
db = client["user_data"]

# Endpoints
router = APIRouter(
    prefix="/user",
    tags=["auth"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)
@router.post("/signup", response_model=User)
async def signup(data: UserCreate):
    """Create a new user and a dedicated collection for their data"""
    # Check if username exists
    users_collection = db.users # Collection "users" just contains user auth data to better assess username inconsistencies
    if users_collection.find_one({"username": data.username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    user_number = get_next_user_number(db)
    hashed_password = get_password_hash(data.password)
    user_dict = {
        "username": data.username,
        "hashed_password": hashed_password,
        "collection_name": f"user_{user_number}"
    }
    
    # Insert user into users collection
    result = users_collection.insert_one(user_dict)
    
    # Create user's personal collection
    user_collection = db[f"user_{user_number}"]
    user_collection.insert_one({"created_at": datetime.now(timezone.utc)})
    
    # Return user data
    return {"id": str(result.inserted_id), "username": data.username}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login to get an access token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(days=EXP_TIME)
    access_token = create_access_token(EXP_TIME, SECRET_KEY, ALGORITHM,
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Store token in user's active tokens (optional for logout functionality)
    random_salt = os.urandom(16)  # Generate a random salt for hashing
    token_hash = get_password_hash(access_token + random_salt.hex())
    users_collection = db.users
    users_collection.update_one(
        {"username": user.username},
        {"$push": {"active_tokens": token_hash, "salt": random_salt.hex()}}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Logout and invalidate the current token"""
    
    # 1. Decode token to get username (without validation)
    token_data = decode_token(token, SECRET_KEY, ALGORITHM)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = token_data.username
    
    # 2. Find the user and their tokens
    users_collection = db.users
    user = users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 3. Check if token hash exists in invalidated_tokens
    invalidated_tokens = user.get("invalidated_tokens", [])
    if token in invalidated_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token already invalidated"
        )
    
    # 4. Check if token hash exists in active_tokens
    active_tokens = user.get("active_tokens", [])
    salts = user.get("salt", [])
    
    # Find the matching token hash
    token_found = False
    token_hash_to_remove = None
    salt_to_remove = None
    
    for i, salt in enumerate(salts):
        if i < len(active_tokens):
            # Check if the calculated hash matches or if verify_password confirms they're the same
            if verify_password(token + salt, active_tokens[i]):
                token_found = True
                token_hash_to_remove = active_tokens[i]
                salt_to_remove = salt
                break
    
    if not token_found:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found in active sessions"
        )
        
    # 5. Invalidate the token
    users_collection.update_one(
        {"username": username},
        {
            "$pull": {
                "active_tokens": token_hash_to_remove,
                "salt": salt_to_remove
            },
            "$push": {
                "invalidated_tokens": token
            }
        }
    )
    
    return {"message": "Successfully logged out"}

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user
