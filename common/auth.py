import os
from fastapi import HTTPException

SECRET_KEY = os.getenv("TOOLS_SECRET_KEY")

def authenticate(access_key: str):
    """
    Authenticates the access_key by comparing it to the SECRET_KEY stored in .env.
    """
    if access_key != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")

def authenticate_user(access_key: str):
    """
    Authenticates the access_key by comparing it to the SECRET_KEY stored in .env.
    """
    if access_key != ACCESS_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True

CHAT_SECRET_KEY = os.getenv("CHAT_SECRET_KEY")

def authenticate_chat(access_key: str):
    """
    Authenticates the access_key by comparing it to the SECRET_KEY stored in .env.
    """
    if access_key != CHAT_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True
