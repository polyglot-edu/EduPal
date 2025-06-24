from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from .auth_utils import TokenData, JWTBearer, PersonalInfo, UserProfileDocument
import httpx
import os

ATLAS_PROJECT_ID = os.getenv("ATLAS_PROJECT_ID")
ATLAS_CLUSTER_NAME = os.getenv("ATLAS_CLUSTER_NAME")
ATLAS_PUBLIC_KEY = os.getenv("ATLAS_PUBLIC_KEY")
ATLAS_PRIVATE_KEY = os.getenv("ATLAS_PRIVATE_KEY")

async def create_search_index(collection_name: str, database_name: str):
    url = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{ATLAS_PROJECT_ID}/clusters/{ATLAS_CLUSTER_NAME}/fts/indexes"

    auth = httpx.DigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY)

    # Define the index body for the embedding vector index
    index_body = {
        "collectionName": collection_name,
        "database": database_name,
        "name": "embedding_vector_index",
        "mappings": {
            "dynamic": False,
            "fields": {
                "content": {
                    "type": "document",
                    "fields": {
                        "embedding": {
                            "type": "knnVector",
                            "dimensions": 768,
                            "similarity": "cosine"
                        },
                        "text": {
                            "type": "string"
                        },
                        "metadata": {
                            "type": "document"
                        }
                    }
                }
            }
        }
    }


    async with httpx.AsyncClient(auth=auth) as client:
        response = await client.post(url, json=index_body)
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to create search index: {response.status_code} {response.text}")
        return response.json()


# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# JWT token handler
security = JWTBearer()

# Helper functions
def get_password_hash(password):
    """Hash a password for storing"""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Verify a stored password against a provided password"""
    return pwd_context.verify(plain_password, hashed_password)

async def get_user(db, username: str):
    """Get user data from the users collection"""
    users_collection = db.users
    user = await users_collection.find_one({"username": username})
    if user:
        hashed_password = user.get("password")
        salt = user.get("password_salt", None)
        return hashed_password, salt
    return None

async def authenticate_user(db, username: str, password: str):
    """Authenticate a user by username and password"""
    hashed_password, salt = await get_user(db, username)
    if not hashed_password:
        return False
    if not verify_password(f"{password}{salt}", hashed_password):
        return False
    return True

def create_access_token(exp_time: int, secret_key: str, algorithm: str, data: dict, expires_delta: Optional[timedelta] = None):
    """Create an access token for the user"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(days=exp_time)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm)
    return encoded_jwt

async def get_current_user(secret_key: str, algorithm: str, token: str = Depends(oauth2_scheme)):
    """Get the current user from the token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def decode_token(token: str, secret_key: str, algorithm: str) -> Optional[TokenData]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except jwt.PyJWTError:
        return None

async def validate_token(db, token: str, secret_key: str, algorithm: str):
    """Validate a request by checking the token"""
    # 1. Decode token to get username (without validation)
    token_data = decode_token(token, secret_key, algorithm)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = token_data.username
    
    # 2. Find the user and their tokens
    users_collection = db.users
    user = await users_collection.find_one({"username": username})
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
    salts = user.get("token_salts", [])
    
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
    
    return username, token_hash_to_remove, salt_to_remove

async def  get_personal_info(user_collection)->PersonalInfo:
    """
    Get the personal information of the user from the collection
    """
    try:
        personal_info_doc = await user_collection.find_one(
            {"document_type": "profile"},
            {"personal_info": 1}
        )
        if personal_info_doc is None:
            raise Exception("Personal information not found")
        personal_info = personal_info_doc.get("personal_info", {})
        return PersonalInfo(**personal_info)
    except Exception as e:
        raise Exception(f"Error in get_personal_info: {e}")

async def get_profile(user_collection)->UserProfileDocument:
    """
    Get the profile of the user from the collection
    """
    try:
        profile_doc = await user_collection.find_one(
            {"document_type": "profile"}
        )
        
        if profile_doc is None:
            raise Exception("Profile not found")
        return profile_doc
    except Exception as e:
        raise Exception(f"Error in get_profile: {e}")
