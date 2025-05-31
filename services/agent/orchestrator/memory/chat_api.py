from fastapi import APIRouter, Depends, HTTPException, status, Body, Header
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
from typing import List, Dict, Optional
from bson.errors import InvalidId
from pydantic import BaseModel
from bson import ObjectId
import os
from motor.motor_asyncio import AsyncIOMotorClient


from .chat_utils import ChatDocumentSimplified, ChatDocument, FactItem, Message, Memory, ChatCreateRequest
from .chat_service import get_chat_history, update_chat_history, send_message
from services.auth.auth_service import get_personal_info
from services.auth.auth_service import validate_token
from common.auth import authenticate_chat as authenticate

# Constants
SECRET_KEY = os.getenv("USERS_SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
EXP_TIME = os.getenv("EXP_TIME", 1)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # MongoDB URI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

# MongoDB connection - using async client
client = AsyncIOMotorClient(MONGO_URI)
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
    - List of ChatDocumentSimplified objects
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Retrieve chat documents from the user's collection
        user_collection = db[username]
        cursor = user_collection.find({"document_type": "chat"})
        # Convert cursor to list
        chat_documents = await cursor.to_list(length=None)  # None means no limit

        # Convert documents to ChatDocumentSimplified objects
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
    - Complete ChatDocument
    """

    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Retrieve chat document from the user's collection
        user_collection = db[username]

        try:
            # Convert string ID to ObjectId if using MongoDB
            chat_document = await user_collection.find_one({"_id": ObjectId(chat_id)})
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
        
        # Explicitly construct the Memory object first
        memory_data = chat_document.get('memory', {})
        memory = Memory(
            key_insights=memory_data.get('key_insights', []),
            important_facts=[FactItem(**fact) for fact in memory_data.get('important_facts', [])],
            summary=memory_data.get('summary', '')
        )

        # Update the chat_document with the properly constructed Memory object
        chat_document['memory'] = memory

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
    - Dictionary with recent_messages (List[Message]), memory (Memory), and personal_info (PersonalInfo)
    """
    
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Retrieve personal information from the user's collection
        user_collection = db[username]

        recent_messages, memory = await get_chat_history(user_collection, chat_id)
        personal_info = await get_personal_info(user_collection)
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



@router.post("/chat/new", response_model=Dict[str, str])
async def create_chat( 
    request: ChatCreateRequest, 
    token: Optional[str] = Header(None, alias="token"), 
    access_key: str = Header(None, alias="access_key")
    ):
    """
    Create a new chat document in the user's collection

    Parameters:
    - request: ChatCreateRequest containing chat_name
    - token: JWT token in headers (key: "token")

    Returns:
    - Dictionary containing chat_id and success message
    """

    try:
        # Authenticate access key
        authenticate(access_key)
        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

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
        print(chat_document.model_dump(by_alias=True))
        result = await user_collection.insert_one(chat_document.model_dump(by_alias=True))

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
async def update_chat_name(chat_id: str, chat_name: str = Body(...), token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """Update the name of a chat document by its ID
    Parameters:
    - chat_id: ID of the chat to update (in URL path)
    - chat_name: New name for the chat (in request body)
    - token: JWT token in headers (required)
    - access_key: Access key in headers (required)
    Returns:
    - Updated ChatDocumentSimplified
    """
    # Authenticate access key
    authenticate(access_key)
    # Get the current user's username
    username, _ , _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
    # Update the chat document in the user's collection
    user_collection = db[username]
    result = await user_collection.update_one(
        {"_id": ObjectId(chat_id)},
        {"$set": {"chat_name": chat_name, "updated_at": datetime.now(tz=timezone.utc)}}
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found or no changes made"
        )
    updated_chat_document = await user_collection.find_one({"_id": ObjectId(chat_id)})
    return ChatDocumentSimplified(**updated_chat_document)

@router.post("/chat/{chat_id}", response_model=List[Message])
async def send_message_to_chat(chat_id: str, message: Message = Body(...), token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key"), model: str =  Header("gemini", alias="model")):
    """Add new messages in a chat document by its ID
    Parameters:
    - chat_id: ID of the chat to update (in URL path)
    - message: Message object to add (in request body)
    - token: JWT token in headers (required)
    - access_key: Access key in headers (required)
    - model: Model to use for the response (default: "gemini")
    Returns:
    - List of Message objects (user message plus LLM internal steps messages plus final response)
    """
    # Authenticate access key
    authenticate(access_key)
    # Get the current user's username
    username, _ , _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
    recent_messages, memory = await get_chat_history(db[username], chat_id)
    personal_info = await get_personal_info(db[username])

    # Update message timestamp to current time
    message.timestamp = datetime.now(tz=timezone.utc)
    # Send the message to the LLM and get the response
    response = await send_message(message, recent_messages, memory, personal_info, model)
    # Add the messages to the chat document
    user_collection = db[username]
    print(response)
    result = await update_chat_history(user_collection, chat_id, response, model)
    if result: return response
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found or error in updating messages"
        )




@router.delete("/chat/{chat_id}", response_model=str)
async def delete_chat(chat_id: str, token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """Delete a chat document by its ID
    Parameters:
    - chat_id: ID of the chat to delete (in URL path)
    - token: JWT token in headers (required)
    - access_key: Access key in headers (required)
    Returns:
    - Success message
    """
    # Authenticate access key
    authenticate(access_key)
    # Get the current user's username
    username, _ , _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
    # Delete the chat document from the user's collection
    user_collection = db[username]
    result = await user_collection.delete_one({"_id": ObjectId(chat_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found"
        )
    return "Chat document deleted successfully"

