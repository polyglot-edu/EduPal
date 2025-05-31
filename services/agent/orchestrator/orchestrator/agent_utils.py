from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Optional
from typing import TypedDict, List
from ..memory.chat_utils import PersonalInfo, Memory, Message

class PerfectedRequest(BaseModel):
    language: str # Language of the chat
    validity: str = "True"  # Indicates if the request is valid
    user_intent: str  # User's intent or goal
    follow_up: str = "None" # Follow-up question or instruction
    planning: str = "False"  # Indicates if the request requires planning
    additional_information: str # All the necessary information for the request
    resources: Optional[List[ObjectId, str, str]] = Field(default_factory=list)  # List of resource IDs, titles and brief descriptions to consider

def perfect_request_prompt(recent_messages: List[Message], memory: Memory, user_info: PersonalInfo, content: str) -> str:
    """
    Generates a prompt for the LLM to perfect the request.
    """
    prompt = f"""Role:\n
You are an expert prompt engineer. Your task is to analyse and perfect a user request based on some context.\n\n
Input:\n
User Query: {content}\n\n
Chat History (Recent): {recent_messages}\n\n
Additional Chat Information: {memory.to_str()}\n\n
User Profile: {user_info.to_str()}\n\n\n

Tasks Output Format:\n
Language: Understand the language the chat is being conducted in.
Validity: Assess the validity of the user query, considering that this is a chat of a system for educational purposes. If the query violates safety or ethical guidelines, write the reason for the rejection. If the query is valid, write "True" and proceed to the next step.
User Intent: Considering all the information at your disposal, understand clearly the user's intent. State the intent in a single sentence.
Follow Up: Understand if the provided context has all the necessary inputs to perform the task required to fulfill the intent. Consider only the user-defined-variables that are absolutely necessary for the task, ignore the knowledge-related-variables, as further grounding can be performed later. If the context is not sufficient, ask the user for the missing information. If the context is sufficient, write "None" and proceed to the next step.
Planning: If the user query is valid and the context is sufficient, decide if the request requires planning. For example, if the user is just asking for a feedback on a text, planning is not necessary (write "False"), while if the user intent is more complex, like generating a lesson, planning is necessary (Write a draft of the steps to be followed to fulfill the intent).
Additional Information: If the user query is valid and the context is sufficient, write a recap of all the additional information useful to fulfill the user intent, in the same language of the chat, that:\n
    - Integrates relevant context from chat history, chat summary, and user profile.
    - Is written in a clear and comprehensive manner.
    - Includes all necessary information.
    - Uses plain language or technical jargon appropriately, depending on the user's background.
    Remember to use the same language of the chat.\n\n  
"""
    return prompt

class Action(BaseModel):
    plan: List[str]  # List of steps to be followed to fulfill the intent
    prompt: str # The prompt to be used for the LLM to perform the task
    grounding: bool = False  # Indicates if the request requires grounding
    grounding_queries: List[str] = Field(default_factory=list)  # List of queries for grounding
    resources: Optional[List[ObjectId, str, str]] = Field(default_factory=list)  # List of resource IDs, titles and brief descriptions to consider
    tool: str = "None"  # The tool to be used for the LLM to perform the task
    next_action: str = "None"  # Placeholder for the next action to be taken

def plan_action_prompt(request: PerfectedRequest, resources: str) -> str:
    """
    Generates a prompt for the LLM to perfect the request.
    """
    prompt = f"""Role:\n
You are expert in logical reasoning and planning. Your task is to plan a series of action to fulfill an initial intent.\n\n
Input:\n
Language: {request.language}\n\n
Intent: {request.user_intent}\n\n
Available Resources: {resources}\n\n
Available Tools: {get_tools()}\n\n

Tasks Output Format:\n
Language: Understand the language the chat is being conducted in.
Validity: Assess the validity of the user query, considering that this is a chat of a system for educational purposes. If the query violates safety or ethical guidelines, write the reason for the rejection. If the query is valid, write "True" and proceed to the next step.
User Intent: Considering all the information at your disposal, understand clearly the user's intent. State the intent in a single sentence.
Follow Up: Understand if the provided context has all the necessary inputs to perform the task required to fulfill the intent. Consider only the user-defined-variables that are absolutely necessary for the task, ignore the knowledge-related-variables, as further grounding can be performed later. If the context is not sufficient, ask the user for the missing information. If the context is sufficient, write "None" and proceed to the next step.
Planning: If the user query is valid and the context is sufficient, decide if the request requires planning. For example, if the user is just asking for a feedback on a text, planning is not necessary (write "False"), while if the user intent is more complex, like generating a lesson, planning is necessary (Write a draft of the steps to be followed to fulfill the intent).
Perfected Prompt: If the user query is valid and the context is sufficient, generate an optimal prompt, in the same language of the chat, that:\n
    - Clearly captures the user's intent.
    - Integrates relevant context from chat history, chat summary, and user profile.
    - Is formatted according to best prompt engineering practices.
    - Is concise but includes all necessary information.
    - Uses plain language or technical jargon appropriately, depending on the user's background.
    - Can be directly fed into another LLM for accurate, contextualized output.\n\n
    Remember to use the same language of the chat.\n\n  
Grounding: Assess your confidence in relying only on your knowledge to fulfill the user intent. If fulfilling the intent requires time dependent information, or specialized knowledge, write "True", if you are 100% sure that you can fulfill the intent with your knowledge, write "False".\n\n

"""
    return prompt

def get_tools() -> List[str]:
    """
    Returns a list of available tools for the LLM to use.
    """
    # Placeholder for the actual implementation
    return [
        "Tool1: Description of Tool1",
        "Tool2: Description of Tool2",
        "Tool3: Description of Tool3"
    ]
  