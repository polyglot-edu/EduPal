import os
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Load JWT config
SECRET_KEY = os.getenv("SECRET_KEY")

def authenticate(token: str):
    print(token)
    print(SECRET_KEY)
    #if token != SECRET_KEY:
        #raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True