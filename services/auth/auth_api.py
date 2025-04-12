from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from common.auth import create_access_token

app = FastAPI()


# User Login Request Model
class LoginRequest(BaseModel):
    username: str
    password: str


# Dummy user database (replace this with MongoDB later)
fake_users_db = {
    "user1": {
        "username": "user1",
        "password": "password123",  # You can later hash this with bcrypt
    }
}

@app.post("/auth/login")
def login(request: LoginRequest):
    user = fake_users_db.get(request.username)
    if not user or request.password != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token with user info
    access_token = create_access_token(data={"sub": request.username})
    return {"access_token": access_token}
