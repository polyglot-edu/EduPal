from bson import ObjectId
from .agent_utils import PerfectedRequest, Action, perfect_request_prompt, plan_action_prompt
from ..memory.chat_utils import PersonalInfo, Memory, Message
from typing import List, Optional
from services.llm_integration.gemini import GeminiLLM

def perfect_request(recent_messages: List[Message], memory: Memory, user_info: PersonalInfo, content: str, model:str = "GEMINI") -> PerfectedRequest:
    """
    Perfects the request by checking its validity and generating a prompt.
    """
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: PerfectedRequest = llm.generate_json(prompt=perfect_request_prompt(recent_messages, memory, user_info, content), response_model=PerfectedRequest)
    except Exception as e:
        raise Exception(f"Error in updateMemory: {e}")
    return response

def plan_action(perfected_request: PerfectedRequest, resources: str, model: str = "GEMINI") -> Action:
    """
    Plans the next action based on the perfected request.
    """
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: Action = llm.generate_json(prompt=plan_action_prompt(perfected_request, resources), response_model=Action)
    except Exception as e:
        raise Exception(f"Error in updateMemory: {e}")
    return response

def ground(query: str, resources: List[ObjectId]) -> str:
    """
    Grounds the query using the provided resources.
    """
    # Placeholder for the actual implementation
    return "Grounded material"

def grounding_to_string(grounding: List[str]) -> str:
    """
    Converts the grounded material to a string format.
    """
    # Placeholder for the actual implementation
    return "Grounded material string"


def map_response_to_message(response: str) -> Message:
    """
    Maps the response from the LLM to a Message object.
    """
    # Placeholder for the actual implementation
    return Message(
        role="assistant",
        content=response,
        timestamp=None,
        in_memory=False,
        resources=[]
    )

def plan_next_message(action: Action) -> Message:
    """
    Plans the next message based on the action.
    """
    # Placeholder for the actual implementation
    return Message(
        role="assistant",
        content="Next message content",
        timestamp=None,
        in_memory=False,
        resources=[]
    )

