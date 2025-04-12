import os
from fastapi import HTTPException

SECRET_KEY = os.getenv("SECRET_KEY")

def authenticate(access_key: str):
    """
    Authenticates the access_key by comparing it to the SECRET_KEY stored in .env.
    """
    if access_key != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True
