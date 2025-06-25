from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Body, Header
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
from typing import List, Dict, Optional
from bson.errors import InvalidId
from pydantic import BaseModel
from bson import ObjectId
import os
from motor.motor_asyncio import AsyncIOMotorClient

from services.agent.grounding.analyse_material.analyse_material_utils import AnalyseMaterialRequest, Analysis
from .upload_service import upload
from services.agent.grounding.analyse_material.analyse_material_utils import AnalyseMaterialRequest

from .chat_utils import STUDENT_SYSTEM_INSTRUCTIONS, ChatDocumentSimplified, ChatDocument, Resource, ResourceDocumentSimplified, ResourceIdsRequest, SendMessageRequest, Message, Memory, ChatCreateRequest, State, UpdateChatRequest
from .chat_service import delete_resources_by_ids, get_chat_info, get_chat_resources, get_complete_resources_by_ids, get_user_resources, update_chat_info, send_message
from services.auth.auth_service import get_personal_info, validate_token
from common.auth import authenticate_chat as authenticate

USER_DATABASE_NAME = "user_data"

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
        cursor = user_collection.find(
            {"document_type": "chat"},
            {
                "_id": 1,
                "chat_name": 1,
                "created_at": 1,
                "updated_at": 1
            }
        )
        # Convert cursor to list
        chat_documents = await cursor.to_list(length=None)  # None means no limit

        # Convert id to string for serialization
        for doc in chat_documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

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
    
@router.get("/resourcelist", response_model=list[ResourceDocumentSimplified])
async def resourcelist(
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Retrieve a list of resource documents for the current user

    Parameters:
    - token: JWT token in headers (key: "token")
    - access_key: Access key in headers (key: "access_key")

    Returns:
    - List of Resource objects
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

        # Retrieve chat documents from the user's collection
        user_collection = db[username]
        
        resource_list = await get_user_resources(user_collection)

        return resource_list

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
        memory = Memory(**memory_data) if memory_data else Memory()

        # Update the chat_document with the properly constructed Memory object
        chat_document['memory'] = memory

        # Convert ObjectId to string for serialization
        if "_id" in chat_document:
            chat_document["_id"] = str(chat_document["_id"])

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

@router.get("/chat/{chat_id}/resources", response_model=list[ResourceDocumentSimplified])
async def chat_resources(
    chat_id: str,
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Retrieve all resource documents (simplified) associated with a specific chat.

    Parameters:
    - chat_id: ID of the chat document (in URL path)
    - token: JWT token in headers (key: "token")
    - access_key: Access key in headers (key: "access_key")

    Returns:
    - List of ResourceDocumentSimplified objects (only 'updated_at' and 'analisys' fields)
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

        user_collection = db[username]

        resource_list = await get_chat_resources(user_collection, chat_id)

        return resource_list

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
  
@router.post("/resources/by-ids", response_model=List[Resource])
async def get_resources_by_ids(
    request: ResourceIdsRequest,
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Retrieve full resource documents by their IDs.

    Parameters:
    - request: JSON body containing 'resource_ids' (list of resource IDs)
    - token: JWT token in headers (key: "token")
    - access_key: Access key in headers (key: "access_key")

    Returns:
    - List of full Resource objects
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

        user_collection = db[username]

        resource_ids = request.resource_ids
        if not resource_ids:
            return []  # No IDs provided

        resource_list = await get_complete_resources_by_ids(user_collection, resource_ids)

        return resource_list

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

@router.post("/delete-resources/by-ids", response_model=int)
async def del_resources_by_ids(
    request: ResourceIdsRequest,
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Delete resource documents by their IDs.

    Parameters:
    - request: JSON body containing 'resource_ids' (list of resource IDs)
    - token: JWT token in headers (key: "token")
    - access_key: Access key in headers (key: "access_key")

    Returns:
    - List of full Resource objects
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)

        user_collection = db[username]

        resource_ids = request.resource_ids
        if not resource_ids:
            return []  # No IDs provided

        deleted_count = await delete_resources_by_ids(user_collection, resource_ids)

        return deleted_count

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

        memory, state  = await get_chat_info(user_collection, chat_id)
        personal_info = await get_personal_info(user_collection)
        return {
            "memory": memory,
            "state": state,
            "personal_info": personal_info if personal_info else None,
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
            memory=Memory(),
            state=State(),
            resources=[]
        )

        # Insert the document
        chat_doc_dict = chat_document.model_dump(by_alias=True)

        # Remove _id if it's None
        if chat_doc_dict.get("_id") is None:
            del chat_doc_dict["_id"]

        print(chat_doc_dict)

        result = await user_collection.insert_one(chat_doc_dict)

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
    # Convert ObjectId to string for serialization
    if updated_chat_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found"
        )
    if "_id" in updated_chat_document:
        updated_chat_document["_id"] = str(updated_chat_document["_id"])
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
    # check if message content is empty or "string"
    if not message.content or message.content.strip() == "" or message.content == "string":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )
    if message.system_instructions is None:
        message.system_instructions = ""

    # Get the current user's username
    username, _ , _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
    g_memory, g_state = await get_chat_info(db[username], chat_id)
    personal_info = await get_personal_info(db[username])
    # if the user is a sutudent, add some custom instruction to make the system behave like a tutor
    if personal_info.role == "student":
        message.system_instructions += STUDENT_SYSTEM_INSTRUCTIONS
    send_message_request = SendMessageRequest(
        chat_id=chat_id,
        message=message,
        memory=g_memory,
        state=g_state,
        personal_info=personal_info if personal_info else None,
        model=model
    )

    # Send the message to the LLM and get the response
    new_messages, next_state = await send_message(send_message_request, user_collection=db[username])
    print("-"*50,"\n")
    print("Message sent to LLM, response received")
    print("\n","-"*50)

    # Add the messages to the chat document
    user_collection = db[username]
    update_chat_request = UpdateChatRequest(
        messages=new_messages, # Include the user message and all LLM messages
        state=next_state,
        model=model
    )
    
    result = await update_chat_info(user_collection, chat_id, update_chat_request)
    print("Chat document updated with new messages")
    if result: return new_messages
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found or error in updating messages"
        )    

@router.post("/chat/{chat_id}/upload", response_model=str)
async def upload_file( chat_id: str, file: Optional[UploadFile] = File(None), url: Optional[str] = Form(None), model: str = Form(...),
    token: str = Header(..., alias="token"),
    access_key: str = Header(..., alias="access_key")
):
    """
    Upload a file (by path) and perform semantic chunking.

    - **file**: The path of the file to upload
    - **db_name**: Database name
    """
    try: 
        authenticate(access_key)

        # check if there is at least one of the two parameters (file or url)
        if not file and not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either file or url must be provided"
            )

        # MongoDB connection - using async client
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[USER_DATABASE_NAME]
        
        # Validate token and get username
        username, _, _ = await validate_token(db, token, SECRET_KEY, ALGORITHM)
        # Get user's personal collection
        collection = db[username]

        # Check existence of the chat document
        count = await collection.count_documents({"_id": ObjectId(chat_id)}, limit=1)
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )

        resource_id = await upload(collection, model, file, url)

        # Update the chat document with the new resource ID
        update_result = await collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$push": {"resources": resource_id}, "$set": {"updated_at": datetime.now(tz=timezone.utc)}}
        )
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found or no changes made"
            )

        return resource_id
    
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")



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

