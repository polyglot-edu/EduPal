from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status

from services.llm_integration.gemini import GeminiLLM
from .chat_utils import UpdateMemoryRequest, Memory, Message, update_memory_prompt
from services.auth.auth_utils import PersonalInfo

# Constants
STM_LENGTH = 4096  # "Min" number of tokens for STM memory
LTM_LENGTH = 12207  # "Max" number of tokens for LTM memory

def updateMemory(request: UpdateMemoryRequest):
    """
    Update the memory of the chat document to regulate STM_LENGTH
    """
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: Memory = llm.generate_json(prompt=update_memory_prompt(request), response_model=Memory)
    except Exception as e:
        raise Exception(f"Error in updateMemory: {e}")
    
    return response



async def get_recent_messages(user_collection, chat_id: str):
    """
    Get the recent messages of the user from the collection
    """
    try:
        chat_doc = await user_collection.find_one({"_id": chat_id}, {"recent_messages": 1})
        if chat_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )
        recent_messages = chat_doc.get("recent_messages", [])
        
        return [Message(**message) for message in recent_messages]
    except Exception as e:
        raise Exception(f"Error in get_recent_messages: {e}")
    
async def get_memory(user_collection, chat_id: str):
    """
    Get the memory of the user from the collection
    """
    try:
        chat_document = await user_collection.find_one({"_id": chat_id}, {"memory": 1})
        if chat_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )
        memory = chat_document.get("memory", [])
        
        return Memory(**memory)
    except Exception as e:
        raise Exception(f"Error in get_memory: {e}")

async def get_chat_history(user_collection, chat_id: str):
    """
    Get both recent messages and memory from the collection in a single query

    Returns:
        tuple: (list of Message objects, Memory object)
    """
    try:
        # Get both fields in a single query
        chat_doc = await user_collection.find_one(
            {"_id": ObjectId(chat_id)},
            {"recent_messages": 1, "memory": 1}
        )

        if chat_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )

        # Process recent messages
        recent_messages = chat_doc.get("recent_messages", [])
        processed_messages = [Message(**message) for message in recent_messages]

        # Process memory
        memory_data = chat_doc.get("memory", {})
        processed_memory = Memory(**memory_data)

        return processed_messages, processed_memory

    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID format"
        )
    except Exception as e:
        raise Exception(f"Error in get_chat_history: {e}")
    



async def update_chat_history(user_collection, chat_id, messages, model):
    contextual_messages = [ msg for msg in messages if msg["role"] in {"assistant", "user"}]
    for message in contextual_messages:
        message["in_memory"] = False
    
    # Update the chat document adding the new messages
    result = user_collection.update_one(
        {"_id": chat_id},
        {
            "$push": {
                "messages": {
                    "$each": [message.model_dump() for message in messages]
                },
                "recent_messages": {
                    "$each": [message.model_dump() for message in contextual_messages]
                }
            },
            "$set": {
                "updated_at": datetime.now(tz=timezone.utc)
            }
        }
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found or no changes made"
        )

    # Update the memory of the chat document to regulate STM_LENGTH
    chat_doc = user_collection.find_one({"_id": chat_id}, {"recent_messages": 1})
    recent_messages: List[Message] = chat_doc.get("recent_messages", [])

    non_in_memory_messages = [Message(**msg) for msg in recent_messages if not msg.in_memory]

    # Get approximate total length of tokens of the recent non_in_memory messages
    total_tokens = 0.0
    for message in non_in_memory_messages:
        total_tokens += len(message.content)/4

    updated_recent_messages = None
    updated_memory = None
    # If the total tokens exceed STM_LENGTH, update the memory and trim the recent messages
    if total_tokens > STM_LENGTH:
        # Update LTM with the new messages
        chat_doc_m = user_collection.find_one({"_id": chat_id}, {"memory": 1})
        memory: Memory = chat_doc_m.get("memory", {})
        update_memory_request: UpdateMemoryRequest = UpdateMemoryRequest(
            LTM_LENGTH, 
            non_in_memory_messages, 
            memory,
            model)
        updated_memory: Memory = updateMemory(update_memory_request)
        updated_recent_messages = non_in_memory_messages.copy()

        # Trim STM to STM_LENGTH
        for message in reversed(non_in_memory_messages):
            message.in_memory = True
            updated_recent_messages.remove(message)
            if total_tokens-len(message.content)/4 < 4096:
                break
            total_tokens -= len(message.content)/4

        # Update the chat document with the new memory and recent messages
        result = user_collection.update_one(
            {"_id": chat_id},
            {
                "$set": {
                    "memory": updated_memory.model_dump(),
                    "recent_messages": [m.model_dump() for m in updated_recent_messages]
                }
            }
        )
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found or no changes made"
            )
    return updated_recent_messages, updated_memory
   
async def send_message(user_collection, chat_id: str, message: str):
    """
    Send a message to the chat document
    """
    try:
        result = user_collection.update_one(
            {"_id": chat_id},
            {
                "$push": {
                    "messages": message.model_dump()
                },
                "$set": {
                    "updated_at": datetime.now(tz=timezone.utc)
                }
            }
        )
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found or no changes made"
            )
        return True
    except Exception as e:
        raise Exception(f"Error in send_message: {e}")

def format_chat_history(messages: List[Message], memory: Memory) -> str:
    """
    Format the chat history for display
    """
    formatted_history = ""
    for message in messages:
        formatted_history += f"{message.role.upper()}: {message.content}\n"
    return formatted_history
