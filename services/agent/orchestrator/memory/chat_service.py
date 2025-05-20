from datetime import datetime, timezone
import json
from typing import List
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status

from services.llm_integration.gemini import GeminiLLM
from .chat_utils import UpdateMemoryRequest, UpdateMemoryResponse, Memory, Message, update_memory_prompt
from services.auth.auth_utils import PersonalInfo
from services.auth.auth_service import get_personal_info

# Constants
STM_LENGTH = 296  # "Min" number of tokens for STM memory
LTM_LENGTH = 12207  # "Max" number of tokens for LTM memory



async def get_recent_messages(user_collection, chat_id: str):
    """
    Get the recent messages of the user from the collection
    """
    try:
        chat_doc = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"recent_messages": 1})
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
        chat_document = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"memory": 1})
        if chat_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )
        memory = chat_document.get("memory", [])
        
        return Memory(**memory)
    except Exception as e:
        raise Exception(f"Error in get_memory: {e}")

async def get_chat_history(user_collection, chat_id: str) -> tuple[List[Message], Memory]:
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
        response: UpdateMemoryResponse = llm.generate_json(prompt=update_memory_prompt(request), response_model=UpdateMemoryResponse)
    except Exception as e:
        raise Exception(f"Error in updateMemory: {e}")
    
    return response

async def update_chat_history(user_collection, chat_id: str, messages: List[Message], model: str="GEMINI") -> tuple[List[Message], Memory]:
    contextual_messages = [msg for msg in messages if msg.role in {"assistant", "user"}]
    for message in contextual_messages:
        message.in_memory = False
    
    # Update the chat document adding the new messages
    result = await user_collection.update_one(
        {"_id": ObjectId(chat_id)},
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
            detail="Chat document not found or no changes made to messages"
        )

    # Update the memory of the chat document to regulate STM_LENGTH
    chat_doc = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"recent_messages": 1})
    recent_messages: List[Message] = [Message(**msg) for msg in chat_doc.get("recent_messages", [])]

    non_in_memory_messages = [msg for msg in recent_messages if not msg.in_memory]

    # Get approximate total length of tokens of the recent non_in_memory messages
    total_tokens = 0.0
    for message in non_in_memory_messages:
        total_tokens += len(message.content)/4
    print(f"Total tokens: {total_tokens}")

    updated_recent_messages = None
    updated_memory = None
    # If the total tokens exceed STM_LENGTH, update the memory and trim the recent messages
    if total_tokens > STM_LENGTH:
        # Get the user's personal information
        personal_info = await get_personal_info(user_collection)
        if personal_info is not None:
            personal_info = personal_info
            personal_info_dict = personal_info.model_dump()
            personal_info_string = json.dumps(personal_info_dict)
        # Update LTM with the new messages
        chat_doc_m = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"memory": 1})
        memory: Memory = Memory(**(chat_doc_m.get("memory", {}))) if chat_doc_m.get("memory") else Memory()
        update_memory_request = UpdateMemoryRequest(
            ltm_length=LTM_LENGTH,
            messages=non_in_memory_messages,
            memory=memory,
            personal_info=personal_info_string,
            model=model
        )
        updated_memory: UpdateMemoryResponse = updateMemory(update_memory_request)
        print(f"Updated memory: {updated_memory}")
        updated_recent_messages = non_in_memory_messages.copy()

        # Update the personal information in the memory if it exists
        if "personal_info" in updated_memory.model_fields_set and updated_memory.personal_info is not None:
            result = await user_collection.update_one(
                {"document_type": "profile"},
                {
                    "$set": {
                        "personal_info": personal_info.model_dump(),
                        "updated_at": datetime.now(tz=timezone.utc)
                    }
                }
            )
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Profile document not found")

        # Trim STM to STM_LENGTH
        for message in non_in_memory_messages:
            message.in_memory = True
            updated_recent_messages.remove(message)
            if total_tokens-len(message.content)/4 < STM_LENGTH:
                break
            total_tokens -= len(message.content)/4
        print(f"Updated recent messages: {updated_recent_messages}")

        memory_dict = {
            "key_insights": updated_memory.memory.key_insights,
            "important_facts": [
                {
                    "key": fact.key,
                    "values": fact.values
                }
                for fact in updated_memory.memory.important_facts
            ],
            "summary": updated_memory.memory.summary
        }
        # Update the chat document with the new memory and recent messages
        result = await user_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {
                "$set": {
                    "memory": memory_dict,
                    "recent_messages": [m.model_dump() for m in updated_recent_messages]
                }
            }
        )
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found or no changes made to memory"
            )
    return updated_recent_messages, updated_memory
   
async def send_message(message: Message, recent_messages: List[Message], memory: Memory, personal_info: PersonalInfo, model: str="GEMINI")-> List[Message]:
    """
    Send a message to the chat document
    """
    try:
        recent_messages_str = "\n".join([msg.to_str() for msg in recent_messages])
        response = GeminiLLM().generate_text(
            prompt=message.content,
            context=memory.to_str(),
            history=recent_messages_str,
            user_info=personal_info.to_str()
        )
        if response is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating response"
            )
        
        user_message = Message(
            role="user",
            content=message.content,
            timestamp=datetime.now(tz=timezone.utc),
            in_memory=False,
            resources=None
        )
        
        assistant_message = Message(
            role="assistant",
            content=response,
            timestamp=datetime.now(tz=timezone.utc),
            in_memory=False,
            resources=None
        )

        messages = [user_message, assistant_message]
            
        return messages
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
