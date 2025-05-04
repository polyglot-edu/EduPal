from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from .auth_utils import UserInDB, TokenData, JWTBearer

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# JWT token handler
security = JWTBearer()

# Helper functions
def get_next_user_number(db):
    """Get the next user number for collection naming"""
    # Check existing collections to determine the next number
    collections = db.list_collection_names()
    user_collections = [c for c in collections if c.startswith("user_")]
    if not user_collections:
        return 1
    
    # Extract numbers from collection names
    numbers = [int(c.split("_")[1]) for c in user_collections]
    return max(numbers) + 1

def get_password_hash(password):
    """Hash a password for storing"""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Verify a stored password against a provided password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    """Get user data from the users collection"""
    users_collection = db.users
    user = users_collection.find_one({"username": username})
    if user:
        user["id"] = str(user["_id"])
        return UserInDB(**user)
    return None

def authenticate_user(db, username: str, password: str):
    """Authenticate a user by username and password"""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

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

def invalidate_token(db, username: str, token: str):
    """Invalidate a user's token"""
    users_collection = db.users
    result = users_collection.update_one(
        {"username": username},
        {"$pull": {"active_tokens": token}},
        {"$push": {"invalidated_tokens": token}}
    )
    return result.modified_count > 0
