from datetime import datetime, timezone
import json
from typing import List
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from mcp.types import TextContent
from pymongo import UpdateOne
from motor.motor_asyncio import AsyncIOMotorCollection
from mcp_server import call_tool
from services.agent.orchestrator.orchestrator.agent_service import ground_response
from services.agent.orchestrator.orchestrator.agent_utils import EXIT_GROUNDING_STRING, RefiningResponse, refining_prompt
from services.llm_integration.gemini import GeminiLLM
from .chat_utils import Resource, ResourceDocumentSimplified, SendMessageRequest, State, UpdateChatRequest, UpdateStructuredMemoryRequest, UpdateStructuredMemoryResponse, Memory, Message, update_structured_memory_prompt
from services.auth.auth_service import get_personal_info
import logging
logger = logging.getLogger(__name__)

# Constants
STM_LENGTH = 4000  # "Min" number of tokens for STM memory
LTM_LENGTH = 12207  # "Max" number of tokens for LTM memory
MAX_STEPS = 3  # Maximum number of steps to perform in the grounding process

async def get_memory(user_collection, chat_id: str)-> Memory:
    """
    Get the recent messages of the user from the collection
    """
    try:
        chat_doc = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"memory": 1})
        if chat_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )
        memory = chat_doc.get("memory", [])
        
        return Memory(**memory)
    except Exception as e:
        raise Exception(f"Error in get_recent_messages: {e}")
    
async def get_state(user_collection, chat_id: str) -> State:
    """
    Get the past intents and models of the user from the collection
    """
    try:
        chat_doc = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"state": 1})
        if chat_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )
        state = chat_doc.get("state", [])
        
        if not state:
            return None, []
        
        return State(**state)
    except Exception as e:
        raise Exception(f"Error in get_state: {e}")

async def get_chat_info(user_collection, chat_id: str) -> tuple[Memory, State]:
    """
    Get both recent messages and memory from the collection in a single query

    Returns:
        tuple: (list of Message objects, Memory object)
    """
    try:
        # Get both fields in a single query
        chat_doc = await user_collection.find_one(
            {"_id": ObjectId(chat_id)},
            {"memory": 1, "state": 1}
        )

        if chat_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )

        # Process the memory field
        memory_data = chat_doc.get("memory", {})
        memory = Memory(**memory_data) if memory_data else Memory()
        # Process the state field
        state_data = chat_doc.get("state", {})
        state = State(**state_data) if state_data else State()

        return memory, state

    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID format"
        )
    except Exception as e:
        raise Exception(f"Error in get_chat_info: {e}")

async def get_chat_messages(user_collection, chat_id: str) -> List[Message]:
    """
    Get the messages of the chat document from the collection
    """
    try:
        chat_doc = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"messages": 1})
        if chat_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat document not found"
            )
        messages = chat_doc.get("messages", [])
        
        return [Message(**message) for message in messages]
    except Exception as e:
        raise Exception(f"Error in get_chat_messages: {e}")


async def get_chat_resources(user_collection: AsyncIOMotorCollection, chat_id: str) -> List[ResourceDocumentSimplified]:
    """
    Get the resources of the chat document from the collection
    """
    try:
        # Retrieve ONLY the 'resources' field from the chat document
        try:
            chat_document = await user_collection.find_one(
                {"_id": ObjectId(chat_id), "document_type": "chat"},
                {"resources": 1}  # projection: only 'resources'
            )
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid chat ID format"
            )

        if chat_document is None or 'resources' not in chat_document:
            #print("Chat document not found or does not contain resources.")
            return []  # No resources found

        resource_ids = chat_document.get('resources', [])
        if not resource_ids:
            #print("No resources linked to this chat document.")
            return []  # No linked resources
        #print(f"Resource IDs found: {resource_ids}")
        
        cursor = user_collection.find({"_id": {"$in": [ObjectId(rid) for rid in resource_ids]}, "document_type": "resource"},
            {
                "_id": 1,
                "uploaded_at": 1,
                "analysis": 1,
                "document_type": 1  # in case your Pydantic model requires it
            }
        )
        resource_documents = await cursor.to_list(length=None)

        # Convert id to string for serialization
        for doc in resource_documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        #print(f"Resource documents found: {resource_documents}")

        # Convert to ResourceDocumentSimplified
        resource_list = [ResourceDocumentSimplified(**doc) for doc in resource_documents]
        
        return resource_list       
    
    except Exception as e:
        raise Exception(f"Error in get_resources: {e}")

async def get_user_resources(user_collection) -> List[ResourceDocumentSimplified]:
    """
    Get the resources of the user document from the collection
    """
    try:
        cursor = user_collection.find({"document_type": "resource"},
            {
                "_id": 1,
                "uploaded_at": 1,
                "analysis": 1,
                "document_type": 1  # in case your Pydantic model requires it
            }
        )
        resource_documents = await cursor.to_list(length=None)

        # Convert id to string for serialization
        for doc in resource_documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        # Convert to ResourceDocumentSimplified
        resource_list = [ResourceDocumentSimplified(**doc) for doc in resource_documents]
        
        return resource_list
    
    except Exception as e:
        raise Exception(f"Error in get_resources: {e}")

async def get_complete_resources_by_ids(user_collection, resource_ids: List[str]) -> List[Resource]:
    """
    Get the resources of the chat document from the collection
    """
    try:
        #print(f"Resource IDs received: {resource_ids}")
        # Fetch the complete resources by their IDs
        resource_cursor = user_collection.find({
            "_id": {"$in": [ObjectId(rid) for rid in resource_ids]},
            "document_type": "resource"
        })
        resource_documents = await resource_cursor.to_list(length=None)
        #print(f"Resource documents found: {resource_documents}")

        # Convert id to string for serialization
        for doc in resource_documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        #print(f"Resource documents found of type: {type(resource_documents)}")
        # Convert to full Resource model
        resource_list = [Resource(**doc) for doc in resource_documents]

        #print(f"Resource documents found of type: {type(resource_list)}")

        return resource_list
    except Exception as e:
        raise Exception(f"Error in get_resources_by_ids: {e}")

async def delete_resources_by_ids(user_collection, resource_ids: List[str])-> int:
    """
    Delete resources by IDs and remove their references from all chat documents.
    """
    try:
        # Validate and convert resource_ids
        valid_object_ids = [ObjectId(rid) for rid in resource_ids if ObjectId.is_valid(rid)]

        if not valid_object_ids:
            return 0  # Nothing to delete

        # Delete the resources
        result = await user_collection.delete_many({
            "_id": {"$in": valid_object_ids},
            "document_type": "resource"
        })

        # Fetch all chat documents (only _id and resources)
        chat_cursor = user_collection.find(
            {"document_type": "chat"},
            {"_id": 1, "resources": 1}
        )
        chat_documents = await chat_cursor.to_list(length=None)

        # Prepare bulk updates
        updates = []
        for chat_doc in chat_documents:
            resources = chat_doc.get("resources", [])
            updated_resources = [rid for rid in resources if rid not in resource_ids]
            if resources != updated_resources:
                updates.append(
                    UpdateOne(
                        {"_id": chat_doc["_id"]},
                        {"$set": {"resources": updated_resources}}
                    )
                )

        # Execute bulk update if needed
        if updates:
            await user_collection.bulk_write(updates)

        return result.deleted_count

    except Exception as e:
        raise Exception(f"Error in delete_resources_by_ids: {e}")



def update_structured_memory(request: UpdateStructuredMemoryRequest):
    """
    Update the memory of the chat document
    """
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: UpdateStructuredMemoryResponse = llm.generate_text(prompt=update_structured_memory_prompt(request), response_model=UpdateStructuredMemoryResponse)
    except Exception as e:
        raise Exception(f"Error in updateMemory: {e}")
    
    return response

async def update_chat_info(user_collection, chat_id: str, request: UpdateChatRequest) -> tuple[Memory, State]:
    #get only assistant and user messages from the request
    contextual_messages:List[Message] = [msg for msg in request.messages if msg.role in {"assistant", "user"}]
    for message in contextual_messages:
        message.in_memory = False
    
    # Get the current memory and state of the chat
    chat_doc = await user_collection.find_one({"_id": ObjectId(chat_id)}, {"memory": 1})
    memory: Memory = Memory(**chat_doc.get("memory"))
    state: State = State(**chat_doc.get("state", {}))
    # If the memory is empty, initialize it
    recent_messages = memory.recent_messages if chat_doc.get("memory") else []
    ##print(f"Current memory: {memory.to_str()}")
    recent_messages.extend(contextual_messages) # Update memory with the new messages
    ##print(f"Recent messages: {[msg.to_str() for msg in recent_messages]}")

    non_in_memory_messages = [msg for msg in recent_messages if not msg.in_memory]
    ##print(f"Non in-memory messages: {[msg.to_str() for msg in non_in_memory_messages]}")

    # Get approximate total length of tokens of the recent non_in_memory messages
    total_tokens = 0.0
    for message in non_in_memory_messages:
        total_tokens += len(message.content)/4
    ##print(f"Total tokens: {total_tokens}")

    updated_recent_messages = recent_messages.copy()
    updated_memory = memory
    updated_memory.recent_messages = non_in_memory_messages
    ##print(f"Updated memory: {updated_memory.to_str()}")
    # If the total tokens exceed STM_LENGTH, update the memory and trim the recent messages
    if total_tokens > STM_LENGTH:
        # Get the user's personal information
        personal_info = await get_personal_info(user_collection)
        if personal_info is not None:
            personal_info = personal_info
            personal_info_dict = personal_info.model_dump()
            personal_info_string = json.dumps(personal_info_dict)
        # Update LTM with the new messages
        update_memory_request = UpdateStructuredMemoryRequest(
            ltm_length=LTM_LENGTH,
            memory=memory,
            personal_info=personal_info_string,
            model=request.model
        )
        updated_structured_memory: UpdateStructuredMemoryResponse = update_structured_memory(update_memory_request)
        ##print(f"Updated memory: {updated_structured_memory}")

        # Update the personal information in the memory if it exists
        if "personal_info" in updated_structured_memory.model_fields_set and updated_structured_memory.personal_info is not None:
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

        for message in non_in_memory_messages:    
            updated_recent_messages.remove(message)
            if total_tokens-len(message.content)/4 < STM_LENGTH:
                break
            total_tokens -= len(message.content)/4
        ##print(f"Updated recent messages: {updated_recent_messages}")

        # Update the memory with the new structured memory and recent messages
        updated_memory.structured_memory = updated_structured_memory.structured_memory
        updated_memory.recent_messages = updated_recent_messages

    # Update the chat document with the new memory, state, and messages
    if request.state is not None:
        state = request.state
    #print(f"State updated: {state.to_str()}")
    #print(f"Updated memory: {updated_memory.to_str()}")

    result = await user_collection.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$push": {
                "messages": {
                    "$each": [message.model_dump() for message in request.messages]
                }
            },
            "$set": {
                "updated_at": datetime.now(tz=timezone.utc),
                "memory": updated_memory.model_dump(),
                "state": state.model_dump()
            }
        }
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat document not found or no changes made to memory"
        )
    return updated_memory, state




async def send_message(request: SendMessageRequest, user_collection: AsyncIOMotorCollection)-> tuple[List[Message], State]:
    """
    Send a message to the chat
    """
    from services.agent.orchestrator.orchestrator.agent_utils import CONFIDENCE_THRESHOLD, GroundingSteps, RequestAnalysis, planner_prompt, RequestAnalysisReviewed, GorundedResponse, step_analysis_prompt
    try:
        ##print(f"Received request: {request.state.to_str() if request.state else 'No state provided'}")
        user_message = request.message
        messages = [user_message]
        # Answer the message using the LLM
        if request.model.upper() == "GEMINI" or request.model is None:
            llm = GeminiLLM()
        else:
            llm = GeminiLLM()
 
        ##print(f"Message: {request.message.content}")
        ##print(f"Memory: {request.memory.to_str()}")
        ##print(f"Personal info: {request.personal_info if request.personal_info else 'None'}")
        ##print(f"Current intent: {request.state.goal_state.current_intent},\n Current models: {request.state.grounding_state.models}")

        resources_message = ""
        if request.message.resources is not None and request.message.resources.__len__() > 0:
            resources_message = f"\n-The user just uploaded some resources. You should 'proceed' if you need to ground the response on those resources."
            
        sys_instructions = ""
        if request.message.system_instructions is not None:
            sys_instructions = f"\nSystemInstructions:{request.message.system_instructions}"
        
        # Create the message request for the LLM
        p_prompt = planner_prompt(request=request)
        ##print(f"Planner prompt: {p_prompt}")
        ##print("-"*50)
        planning_response: RequestAnalysis = llm.generate_text(prompt=p_prompt, response_model=RequestAnalysis)
        if planning_response is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating response"
            )
        #print(f"Planning Response: {planning_response}")
        #print("-"*50)

        if planning_response.validity != "True":
            response_message = planning_response.validity
            assistant_message = Message(
                role="assistant",
                content=response_message,
                system_instructions=planning_response.reasoning
            )
            messages.append(assistant_message)
            return messages, request.state
        
        if planning_response.answer == "None":
            request.state.reset()
            return messages, request.state
        
        elif planning_response.answer == "Proceed":
            if planning_response.goal_state.steps_done.__len__() == 0:
                request.state.grounding_state.reset()
            response_message = "\n".join(planning_response.goal_state.next_steps)
            assistant_message = Message(
                role="planner",
                content=response_message,
                system_instructions=planning_response.reasoning
            )
            messages.append(assistant_message)

            # Update the state
            new_state = request.state
            new_state.goal_state = planning_response.goal_state
            request_analysis_reviewed = RequestAnalysisReviewed(
                language=planning_response.language,
                state=request.state,
                message=request.message.content
            )

            steps = 0
            confidence = 0
            # Perform current task
            while steps < MAX_STEPS and confidence <CONFIDENCE_THRESHOLD and request_analysis_reviewed.state.grounding_state.last_grounding_step != GroundingSteps.CHAT_HISTORY.value:
                steps += 1
                #print("-"*50)
                #print(f"Grounded info:\n")
                #print(request_analysis_reviewed.state.grounding_state.grounded_info)
                #print("\n"*3)
                #print(request_analysis_reviewed.state.grounding_state.last_grounding_step)
                #print("-"*50)

                # fill in the prompt template and call the LLM
                s_prompt = await step_analysis_prompt(request=request_analysis_reviewed)
                s_prompt = s_prompt + sys_instructions + resources_message
                #print("\nResources message:", resources_message,"\n")
                ##print(f"Step analysis prompt: {s_prompt}")
                ##print("-"*50)
                grounding_response: GorundedResponse = llm.generate_text(
                    prompt=s_prompt,
                    response_model=GorundedResponse
                )
                grounding_response = GorundedResponse(**grounding_response.model_dump())
                
                if grounding_response is None:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error generating grounding response"
                    )
                #print(f"Grounding response: {grounding_response}")
                #print("-"*50)
                
                # If needed, ask a follow-up question 
                if grounding_response.follow_up != "None":
                    message_content = grounding_response.follow_up
                    follow_up_message = Message(
                        role="assistant",
                        content=message_content,
                        system_instructions=grounding_response.reasoning
                    )
                    messages.append(follow_up_message)
                    return messages, request_analysis_reviewed.state
                
                # If the confidence is above the threshold, return the response
                if grounding_response.confidence >= CONFIDENCE_THRESHOLD or grounding_response.grounding == GroundingSteps.CHAT_HISTORY.value:
                    #print(f"Confidence reached: {grounding_response.confidence}")
                    response_message = grounding_response.answer
                    assistant_message = Message(
                        role="grounding",
                        content=response_message,
                        system_instructions=grounding_response.reasoning
                    )
                    messages.append(assistant_message)

                    if grounding_response.tool_call != "None":
                        #print("-"*50,"\nTool call:", grounding_response.tool_call,"\n", "-"*50)
                        tool_call_dict: dict = json.loads(grounding_response.tool_call)
                        tool_name = tool_call_dict.get("tool_name")
                        tool_params = tool_call_dict.get("parameters")
                        if tool_name is not None and tool_name != "None" and tool_name != "" and tool_params is not None and tool_params != "None" and tool_params != "":
                            if isinstance(tool_params, str):
                                converted_tool_params = json.loads(tool_params)
                            else:
                                converted_tool_params = tool_params
                            # call your MCP server call_tool function here asynchronously
                            #print("-"*50,"\nCalling tool:", tool_name,"\n", "-"*50)
                            #print("-"*50,"\nTool parameters:", converted_tool_params,"\n", "-"*50)
                            tool_response: list[TextContent] = await call_tool(tool_name, tool_params)
                            #print("-"*50,"\nTool response:", tool_response[0].text,"\n", "-"*50)
                            tool_text = tool_response[0].text if tool_response else "No response"
                            if tool_text is not None and isinstance(tool_response[0], TextContent):
                                # Update the state
                                request_analysis_reviewed.state.grounding_state.models.append(tool_text)
                                tool_message = Message(
                                    role="tool",
                                    content=tool_text
                                )
                                messages.append(tool_message)
                            else: 
                                logger.error("Tool response is None")
                                #print("-"*50,"\nTool response is None\n", "-"*50)
                    
                    new_state.goal_state.steps_done.append(planning_response.goal_state.next_steps[0])
                    new_state.goal_state.next_steps.pop(0)  # Remove the first step as it is being processed

                    # Refine the final answer
                    prompt = refining_prompt(planning_response.language, messages, new_state, sys_instructions, request.personal_info)
                    #call llm
                    refining_response: RefiningResponse = llm.generate_text(prompt=prompt, response_model=RefiningResponse)
                    refining_response = RefiningResponse(**refining_response.model_dump())
                    if refining_response is None:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error generating response"
                        )
                    #print(f"Refining response: {refining_response}")
                    #print("-"*50)
                    response_message = refining_response.refined_answer
                    assistant_message = Message(
                        role="assistant",
                        content=response_message,
                        system_instructions=refining_response.reasoning
                    )
                    messages.append(assistant_message)

                    return messages, new_state
                
                # If the confidence is below the threshold, perform grounding to gather more information
                elif grounding_response.confidence < CONFIDENCE_THRESHOLD:
                    #print(f"Confidence not reached: {grounding_response.confidence}\n")
                    grounded_information: str = await ground_response(
                        user_collection, 
                        request.chat_id,
                        grounding_response.grounding,
                        request.message.resources if request.message.resources is not None else [],
                        grounding_response.answer,
                        planning_response.language,
                        planning_response.goal_state.to_str(),
                        grounding_response.reasoning,
                        request.model)
                    #print(f"\nGrounded information: {grounded_information}\n")
                    request_analysis_reviewed.state.grounding_state.grounded_info = grounded_information
                    request_analysis_reviewed.state.grounding_state.last_grounding_step = grounding_response.grounding.value
                
            # If the confidence is below the threshold and no more grounding can be done, return what you have so far
            response_message = grounding_response.answer
            assistant_message = Message(
                role="grounding",
                content=response_message,
                system_instructions=f"{grounding_response.reasoning}\n\nConfidence: {grounding_response.confidence}%"
            )
            messages.append(assistant_message)

            # Refine the final answer
            prompt = refining_prompt(planning_response.language, messages, new_state, sys_instructions, request.personal_info)
            exit_string = EXIT_GROUNDING_STRING
            prompt = prompt + exit_string
            #call llm
            refining_response: RefiningResponse = llm.generate_text(prompt=prompt, response_model=RefiningResponse)
            refining_response = RefiningResponse(**refining_response.model_dump())
            if refining_response is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error generating response"
                )
            #print(f"Refining response: {refining_response}")
            #print("-"*50)
            response_message = refining_response.refined_answer
            assistant_message = Message(
                role="assistant",
                content=response_message,
                system_instructions=refining_response.reasoning
            )
            messages.append(assistant_message)
            return messages, request_analysis_reviewed.state

        else: # This is the case where the response is a follow-up message to the user or a direct response
            response_message = planning_response.answer
            assistant_message = Message(
                role="assistant",
                content=response_message,
                system_instructions=planning_response.reasoning
            )
            messages.append(assistant_message)
            # Update the state
            new_state = request.state
            ##print(f"New state: {new_state.to_str()}")
            new_state.goal_state = planning_response.goal_state

            if planning_response.goal_state.next_steps.__len__() == 1:
                new_state.reset()
                ##print(f"New state after reset: {new_state.to_str()}")

            return messages, new_state

    except Exception as e:
        raise Exception(f"Error in send_message: {e}")
