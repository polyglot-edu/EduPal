from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
from pymongo import MongoClient
import os
from typing import List, Optional
from services.auth.auth_service import validate_token
from ..memory.chat_utils import Memory, Message, PersonalInfo
from ..memory.chat_service import get_chat_history, get_personal_info, update_chat_history, format_chat_history
from services.llm_integration.gemini import GeminiLLM
from .agent_utils import PerfectedRequest, Action
from .agent_service import perfect_request, plan_action, ground, grounding_to_string, map_response_to_message, plan_next_message

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
    prefix="/agent",
    tags=["chat"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/chat/{chat_id}/send_message", response_model=str)
async def send_message(chat_id: str, message: Message, token: str = Depends(oauth2_scheme), recent_messages: Optional[List[Message]] = None, memory: Optional[Memory] = None, user_info: Optional[PersonalInfo] = None):
    """send a message in a chat"""
    # Get the current user's username
    username, _ , _ = validate_token(db, token, SECRET_KEY, ALGORITHM)
    # Create a new chat document in the user's collection
    user_collection = db[username]
    messages: List[Message] = [message]
    
    # Get everything ready
    if recent_messages is not None and memory is not None and user_info is not None:
        messages = recent_messages
        memory = memory
        user_info = user_info
    else:
        recent_messages, memory = await get_chat_history(user_collection, chat_id)
        user_info = await get_personal_info(user_collection)
    content = message.content
    resources = message.resources_to_str()

    # Perfect the request
    perfected_request: PerfectedRequest = await perfect_request(recent_messages, memory, user_info, content, model="GEMINI")
    if perfected_request.validity == "True":
        messages.append(Message(
            role="internal_pf", 
            content=f"{perfected_request.user_intent}, {perfected_request.additional_information}", 
            timestamp=datetime.now(tz=timezone.utc), 
            in_memory=False, 
            resources= None)
            )
    else:
        return perfected_request.validity
    
    if perfected_request.follow_up.lower() != "none":
        messages.append(Message(
            role="assistant", 
            content=perfected_request.follow_up, 
            timestamp=datetime.now(tz=timezone.utc), 
            in_memory=False, 
            resources= None)
            )
        return perfected_request.follow_up

#############################################################################################################################
    # Plan action
    action: Action = await plan_action(perfected_request, resources, model="GEMINI")

    # Grounding
    grounded_material = "None"
    if action.grounding == True:
        grounding: List[str, str, str] = [] # List of tuples (query, content, resource)
        for query in action.grounding_queries:
            grounding.append(await ground(query, action.resources))
        grounded_material = grounding_to_string(grounding)
        
    messages.append(Message(
        role="internal_ap",
        content=f"PROMPT:{action.prompt} \n\n CONTEXT:{grounded_material}",
        timestamp=datetime.now(tz=timezone.utc),
        in_memory=False,
        resources=action.resources)
        )
        
    # Execute action
    response = await GeminiLLM.generate_text(
        prompt = action.prompt,
        context = grounded_material,
        history = format_chat_history(recent_messages, memory),
        options={"temperature": 0.0, "max_output_tokens": 1550},
        user_info = user_info,
        instructions = action.instructions
    )

    response_message: Message = map_response_to_message(response)
    messages.append(response_message)

    # Update chat history
    recent_messages, memory = await update_chat_history(
        user_collection,
        chat_id,
        messages
    )

    next_action = action.next_action
    next_message: Message = plan_next_message(action) 

    return response_message, next_action, next_message, recent_messages, memory

