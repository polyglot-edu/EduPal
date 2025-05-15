from fastapi import APIRouter, Depends, HTTPException, status, Body, Header
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
from typing import List, Dict, Optional
from bson.errors import InvalidId
from pymongo import MongoClient
from pydantic import BaseModel
from bson import ObjectId
import os

from .chat_utils import ChatDocumentSimplified, ChatDocument, Message, Memory, ChatCreateRequest
from .chat_service import get_chat_history, update_chat_history
from services.auth.auth_utils import PersonalInfo
from services.auth.auth_service import get_personal_info
from services.auth.auth_service import validate_token
from common.auth import authenticate_chat as authenticate

# Constants
SECRET_KEY = os.getenv("USERS_SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
EXP_TIME = os.getenv("EXP_TIME", 1)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # MongoDB URI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

# MongoDB connection
client = MongoClient(MONGO_URI)
db = client["user_data"]

# Endpoints
router = APIRouter(
    prefix="/user",
    tags=["chat"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.get("/chatlist", response_model=list[ChatDocumentSimplified])
async def chatlist(
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Retrieve a list of chat documents for the current user

    Parameters:
    - token: JWT token in headers (key: "token")
    - access_key: Access key in headers (key: "access_key")

    Returns:
    - List of simplified chat documents
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Retrieve chat documents from the user's collection
        user_collection = db[username]
        chat_documents = user_collection.find({"document_type": "chat"})
        chat_list = [ChatDocumentSimplified(**doc) for doc in chat_documents]

        return chat_list

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
    
@router.get("/chat/{chat_id}", response_model=ChatDocument)
async def chat(
    chat_id: str,
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Retrieve a chat document by its ID

    Parameters:
    - chat_id: ID of the chat to retrieve (in URL path)
    - token: JWT token in headers (key: "token")
    - access_key: Access key in headers (key: "access_key")

    Returns:
    - Complete chat document
    """

    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Retrieve chat document from the user's collection
        user_collection = db[username]

        try:
            # Convert string ID to ObjectId if using MongoDB
            chat_document = user_collection.find_one({"_id": ObjectId(chat_id)})
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid chat ID format"
            )

        if chat_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )

        return ChatDocument(**chat_document)

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
    
@router.get("/chat/{chat_id}/history", response_model=Dict)
async def get_history(
    chat_id: str,
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Retrieve recent messages, memory from the chat, and user personal information from the collection

    Parameters:
    - chat_id: ID of the chat to retrieve history for (in URL path)
    - token: JWT token in headers (key: "token")
    - access_key: Access key in headers (key: "access_key")

    Returns:
    - Dictionary with recent_messages and memory
    """
    
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Retrieve personal information from the user's collection
        user_collection = db[username]

        recent_messages, memory = await get_chat_history(user_collection, chat_id)
        personal_info =PersonalInfo(**await get_personal_info(user_collection))
        return {
            "recent_messages": recent_messages,
            "memory": memory,
            "personal_info": personal_info
        }

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



@router.post("/chat", response_model=Dict[str, str])
async def create_chat( request: ChatCreateRequest, token: Optional[str] = Header(None, alias="token"), access_key: str = Header(None, alias="access_key")):
    """
    Create a new chat document in the user's collection

    Parameters:
    - request: ChatCreateRequest containing chat_name
    - token: JWT token in headers (key: "token")

    Returns:
    - Dictionary containing chat_id and message
    """
    
    if not access_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access key is required"
        )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required"
        )

    try:
        # Authenticate access key
        authenticate(access_key)
        # Validate token and get username
        username, _, _ = validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Get user's collection
        user_collection = db[username]

        # Create new chat document
        chat_document = ChatDocument(
            chat_name=request.chat_name,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            recent_messages=[],
            messages=[],
            memory=Memory()
        )

        # Insert the document
        result = user_collection.insert_one(chat_document.model_dump(by_alias=True))

        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat document"
            )

        return {
            "chat_id": str(result.inserted_id),
            "message": f"Chat '{request.chat_name}' created successfully"
        }

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



@router.put("/chat/{chat_id}/change_name", response_model=ChatDocumentSimplified)
async def update_chat_name(chat_id: str, chat: ChatDocumentSimplified, token: str = Depends(oauth2_scheme)):
    """Update the name of a chat document by its ID"""
    # Get the current user's username
    username, _ , _ = validate_token(db, token, SECRET_KEY, ALGORITHM)
    # Update the chat document in the user's collection
    user_collection = db[username]
    result = user_collection.update_one(
        {"_id": chat_id},
        {"$set": {"chat_name": chat.chat_name}}
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found or no changes made"
        )
    updated_chat_document = user_collection.find_one({"_id": chat_id})
    return ChatDocumentSimplified(**updated_chat_document)

@router.put("/chat/{chat_id}/update", response_model=str)
async def update_chat(chat_id: str, messages: List[Message], model: str = "Gemini", token: str = Depends(oauth2_scheme)):
    """Add new messages in a chat document by its ID"""
    # Get the current user's username
    username, _ , _ = validate_token(db, token, SECRET_KEY, ALGORITHM)

    # Get only the messages that are either assistant or user, avoid inner-processes messagess, and set in_memory to False
    user_collection = db[username]
    result = await update_chat_history(user_collection, chat_id, messages, model)
    if result: return "Messages added successfully"
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found or error in updating messages"
        )




@router.delete("/chat/{chat_id}", response_model=str)
async def delete_chat(chat_id: str, token: str = Depends(oauth2_scheme)):
    """Delete a chat document by its ID"""
    # Get the current user's username
    username, _ , _ = validate_token(db, token, SECRET_KEY, ALGORITHM)
    # Delete the chat document from the user's collection
    user_collection = db[username]
    result = user_collection.delete_one({"_id": chat_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found"
        )
    return "Chat document deleted successfully"

