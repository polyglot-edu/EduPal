from fastapi import APIRouter, Depends, HTTPException, status, Header, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta, datetime, timezone
import os
from motor.motor_asyncio import AsyncIOMotorClient

from common.auth import authenticate_user as authenticate
from .auth_utils import UserCreateRequest, User, Token, PersonalInfo, UserProfileDocument, UserPreferences
from .auth_service import create_search_index, get_password_hash, authenticate_user, create_access_token, validate_token, get_profile
import logging
logger = logging.getLogger(__name__)

# Constants
SECRET_KEY = os.getenv("USERS_SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
EXP_TIME = int(os.getenv('EXP_TIME', '90'))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # MongoDB URI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

# MongoDB connection - using async client
client = AsyncIOMotorClient(MONGO_URI)
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
async def signup(request: UserCreateRequest = Body(...), access_key: str = Header(..., alias="access_key") ):
    """
    Create a new user profile with default values.
    Parameters:
    - request: UserCreateRequest object containing username, password, and role (defaults to "student").
    - access_key: Access key for authentication (in headers).
    Returns:
    - User object containing the user's ID and username.
    """
    try:
        # Authenticate access key
        authenticate(access_key)
        # First, check if username already exists
        if await db.users.find_one({"username": request.username}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

        new_role = "student"  # Default role if not provided
        if request.role:
            new_role = request.role
        personal_info = PersonalInfo(
            role=new_role,
            name=None,
            age=None,
            location=None,
            interests=None,
            education_level=None
        )
        # Create the full profile document with defaults
        user_profile = UserProfileDocument(
            personal_info=personal_info,
            # preferences will use its defaults
        )

        # Create user document with profile and credentials
        salt = os.urandom(16)
        salted_password = request.password + salt.hex()
        hashed_password = get_password_hash(salted_password)

        username = request.username
        # Create user's personal collection
        user_collection = db[username]

        # Insert the profile document into user's collection
        result = await user_collection.insert_one(user_profile.model_dump(by_alias=True))

        # Insert user credentials into users collection
        users_result =await db.users.insert_one({
            "username": username,
            "password": hashed_password,
            "password_salt": salt.hex(),
            "role": new_role
        })

        if (not result.inserted_id or not users_result.inserted_id) and username is not None:
            # If profile insertion failed, cleanup and raise error
            await db[username].drop()
            await db.users.delete_one({"username": username})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user profile"
            )
        
        await create_search_index(collection_name=username, database_name=db.name)

        user = User(
            id=str(users_result.inserted_id),
            username=request.username
        )
        return user

    except Exception as e:
        if request.username is not None:
            # Cleanup in case of any error
            try:
                await db[request.username].drop()
                await db.users.delete_one({"username": request.username})
            except Exception as cleanup_error:
                # Log the cleanup error but don't raise it
                logger.error(f"Cleanup error: {cleanup_error}")
                #print(f"Cleanup error: {cleanup_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), access_key: str = Header(..., alias="access_key")):
    """Login to get an access token
    Parameters:
    - form_data: OAuth2PasswordRequestForm object containing username and password.
    - access_key: Access key for authentication (in headers).
    Returns:
    - JWT Token object containing the access token and token type (Bearer).
    """
    try:
        # Authenticate user
        authenticate(access_key)

        user = await authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(days=EXP_TIME)
        access_token = create_access_token(EXP_TIME, SECRET_KEY, ALGORITHM,
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        
        # Store token in user's active tokens (optional for logout functionality)
        random_salt = os.urandom(16)  # Generate a random salt for hashing
        token_hash = get_password_hash(access_token + random_salt.hex())
        users_collection = db.users
        result = await users_collection.update_one(
            {"username": form_data.username},
            {"$push": {"active_tokens": token_hash, "token_salts": random_salt.hex()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user's active tokens"
            )
        
        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.post("/logout")
async def logout(token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """Logout and invalidate the current token
    Parameters:
    - token: JWT token to be invalidated (in headers).
    - access_key: Access key for authentication (in headers).
    Returns:
    - Message indicating successful logout.   
    """
    try:
        # Authenticate access key
        authenticate(access_key)
        # Decode and validate the token
        username, token_hash_to_remove, salt_to_remove = await validate_token(db, token, SECRET_KEY, ALGORITHM)
        
        # Invalidate the token
        users_collection = db.users
        result = await users_collection.update_one(
            {"username": username},
            {
                "$pull": {
                    "active_tokens": token_hash_to_remove,
                    "token_salts": salt_to_remove
                },
                "$push": {
                    "invalidated_tokens": token
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to invalidate token"
            )
        
        return {"message": "Successfully logged out"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.delete("/delete")
async def delete_user(token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """Delete user account
    Parameters:
    - token: JWT token for authentication (in headers).
    - access_key: Access key for authentication (in headers).
    Returns:
    - Message indicating successful deletion.
    """
    try:
        # Authenticate access key
        authenticate(access_key)
        # Delete user's personal collection
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
        user_collection = db[username]
        user_collection.drop()
        # Delete user from users collection
        users_collection = db.users
        result = await users_collection.delete_one({"username": username})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return {"message": "User deleted successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )



@router.get("/profile", response_model=UserProfileDocument)
async def read_users_me(token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """Get current user information
    Parameters:
    - token: JWT token for authentication (in headers).
    - access_key: Access key for authentication (in headers).
    Returns:
    - UserProfileDocument object containing the user's profile information.
    """
    try: 
        # Authenticate access key
        authenticate(access_key)
        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
        # Get user's personal collection
        user_collection = db[username]
        # Get user's profile document
        user_profile: UserProfileDocument = await get_profile(user_collection)
        return user_profile

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.put("/update/personal_info", response_model=str)
async def update_personal_info(personal_info: PersonalInfo = Body(...), token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """Update or reset the user's personal info
    Parameters:
    - personal_info: PersonalInfo object containing the user's personal information (in body).
    - token: JWT token for authentication (in headers).
    - access_key: Access key for authentication (in headers).
    Returns:
    - Message indicating successful update.
    """
    try:
        # Authenticate access key
        authenticate(access_key)
        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
        user_collection = db[username]

        result = await user_collection.update_one(
            {"document_type": "profile"},
            {
                "$set": {
                    "personal_info": personal_info.model_dump(),
                    "updated_at": datetime.now(tz=timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Profile document not found")

        return "Personal info updated successfully"

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.put("/update/preferences", response_model=str)
async def update_preferences(preferences: UserPreferences = Body(...), token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """Update or reset the user's personal info
    Parameters:
    - preferences: UserPreferences object containing the user's preferences (in body).
    - token: JWT token for authentication (in headers).
    - access_key: Access key for authentication (in headers).
    Returns:
    - Message indicating successful update.
    """
    try:
        # Authenticate access key
        authenticate(access_key)
        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
        user_collection = db[username]

        result = await user_collection.update_one(
            {"document_type": "profile"},
            {
                "$set": {
                    "preferences": preferences.model_dump(),
                    "updated_at": datetime.now(tz=timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Profile document not found")

        return "Preferences updated successfully"

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
