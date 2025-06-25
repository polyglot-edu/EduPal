from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from typing import List

from services.auth.auth_utils import PersonalInfo
from ..chat.chat_utils import GoalState, SendMessageRequest, State, Message
from services.agent.tools.tools_manager import get_tools, get_tools_short
from enum import Enum

CONFIDENCE_THRESHOLD = 75

#-----------------------------------------Planning-----------------------------------------
class RequestAnalysis(BaseModel):
    language: str # Language of the chat
    validity: str  # Indicates if the request is valid ("True") or reason for rejection
    goal_state: GoalState  # Current state of the chat
    reasoning: str  # Reasoning for the plan
    answer: str  # Direct answer to the user query, if applicable

def planner_prompt(request: SendMessageRequest) -> str:
    """
    Generates a prompt for the LLM to perfect the request and plan next actions with minimal and necessary steps.
    """

    recent_messages_str = "\n".join([msg.to_str() for msg in request.memory.recent_messages])
    structured_memory = request.memory.structured_memory.to_str()

    state = request.state.to_str() if request.state else ""

    if request.message.resources and len(request.message.resources) > 0:
        resources = ("\n-The user just uploaded some resources. "
                     "You should 'proceed' if you need to ground the response on those resources.")
    else:
        resources = ""

    sys_instructions = (f"\nSystemInstructions:{request.message.system_instructions}"
                        if request.message.system_instructions else "")

    prompt = f"""Role:
You are an educator assistant, expert in logical reasoning and minimalistic planning. 
Your goal is to generate *only the essential steps* to fulfill the user request. 

Important:
- Before planning, assess if the user's intent is already clear and directly actionable.
- If the request is straightforward and all required information is available, provide a direct plan or instruct to 'Proceed' without unnecessary decomposition.
- Do NOT generate generic or exploratory steps unless strictly required to reach the user's explicit goal.
- Respect the specificity of the user's intent. Plan only what is truly necessary to fulfill this precise request.

Input:
Chat History (Recent): {recent_messages_str}
Additional Chat Information: {structured_memory}
User Info: {request.personal_info.to_str()}
{state}
User Query: {request.message.content}

Available Tools: {get_tools_short()}

Tasks Output Format:
Language: State the chat language.

Validity: Evaluate the validity of the user request for educational purposes. 
- If the query violates safety or ethical guidelines, specify why (in the detected language).
- Otherwise, write "True".

GoalState:
{request.state.goal_state.toString()}

Reasoning: Briefly explain your planning choices and how they serve the final goal and user intent (in the detected language).

Answer:
- If the intent is clear and you have enough data to answer immediately, provide the direct answer (in user language).
- If the intent is unclear or ambiguous, ask a specific clarifying question (in user language).
- If complex actions, grounding, or further decomposition are necessary, write "Proceed" to delegate to the next step.
- If the chat is ending, thank the user politely or write "None" if no output is needed.

Notes: {resources}

- Be polite and respectful.
- Small talk or casual conversation is valid intent — respond appropriately without overplanning.
{sys_instructions}
"""
    return prompt

class GroundingSteps(Enum):
    USER_RESOURCES = "user resources (a set of resources uploaded by the user. Useful when the user wants to work with proprietary, private, or specific content.)"  # Step for user resources grounding
    OERS = "Open Educational Resources database (a set of curated, reliable, and designed resources for educational use. Useful when the user requires delicate and non temporal dependent factual knowledge and/or user resources are not sufficient.) "  # Step for Open Educational Resources grounding
    WEB_SEARCH = "web search (general web search. Useful when the user requires general factual knowledge / time dependent information and/or user resources and OERs are not sufficient)"  # Step for web search grounding
    #CHAT_HISTORY = "chat history"  # Step for chat history grounding

    def to_str():
        return f"{GroundingSteps.USER_RESOURCES.value}, {GroundingSteps.OERS.value}, {GroundingSteps.WEB_SEARCH.value}"

class RequestAnalysisReviewed(BaseModel):
    language: str # Language of the chat
    state: State  # Current state of the chat
    message: str # User message to be analyzed

class GorundedResponse(BaseModel):
    follow_up: str  # Follow-up question or clarification needed, "None" if not needed
    confidence: int  # Confidence percentage in fulfilling the intent
    reasoning: str  # Reasoning for the confidence assessment
    grounding: GroundingSteps  # Grounding step to perform
    answer: str # The answer to the user query if the confidence is above a certain threshold
    tool_name: str  # Name of the tool to be used, if applicable
    tool_parameters: str  # Parameters for the tool, if applicable


#---------------------------------------------Grounding---------------------------------------------

def step_analysis_prompt(request: RequestAnalysisReviewed) -> str:
    """
    Generates a prompt for the LLM to answer a request or require further grounding
    """

    prompt = f"""Role:
You are an expert educator and assistant designed to complete user requests efficiently and correctly.

Today's Date: {datetime.now().strftime("%Y-%m-%d")} 
// This is the current date. If the required information depends on events or data after your last training, your internal knowledge may be outdated.

User Language: {request.language}
{request.state.to_str()}
User Message: {request.message}
Available Tools: {get_tools()}

Tasks Output Format:

Follow Up:
Determine if you have ALL the necessary information to complete the task from:
1. Internal knowledge,
2. Provided context (messages, state),
3. Uploaded resources, or grounding options.

- If any missing information CAN be retrieved via resources or grounding (web or database), write "None" — do NOT ask the user.
- You may ONLY ask the user if the missing information concerns personal preferences, opinions, or goals that are NOT discoverable via grounding.

Confidence (0-100):
    Assess your ability to fulfill the user's request using:
        1. Your internal knowledge.
        2. The provided context, including:
            - The user's message,
            - The state object (which may include grounded or externally retrieved information),

    Rules:
        - If the task depends on recent, time-sensitive, or factual information:
            - Check if the required data is **already present** in the context or state.
            - If it is present and sufficient, provide a non-zero confidence score.
            - Check if the user is referring to specific uploaded resources (you should understand this from the message, if the user is referring to something either specifically or vaguely)
            - If you need to ground on user resources, OERs database or web search, set Confidence to **0**.
            - If it's missing or incomplete, set Confidence to **0**.
            - If tool usage is needed but any required parameters are missing, set Confidence to **0**.
            - If the user's request requires personal preferences or goals and they are missing, Confidence may be above 0 **only** if this does not affect task completion.
        - If the user is referring to something specific and they recently uploded something, consider that they might want to use that specific resource.
        - Otherwise, give a realistic confidence score based on what is already known or provided.

    Reminder: Do **not** assume grounding is needed again if time-sensitive or factual info is already present in the state or context. Analyze before deciding.

    Important:
    - If the task depends on time-sensitive or external data, check if the relevant and up-to-date information has **already been grounded** in the provided context or state.
    - Only set Confidence to **0** if the required info is **not already included** in the provided grounding.
    - If the information is available in the state (e.g. web search results, database grounding), and it answers the user's query sufficiently, Confidence should reflect that.

ConfidenceReasoning:
Briefly justify your confidence score (in {request.language}).
- Explicitly say whether any grounded info already addresses the user's request.
- Explain why no further grounding is needed or why it is needed (if applicable).

Grounding:
- IF your Confidence < {CONFIDENCE_THRESHOLD}, you MUST select the most appropriate grounding source from: {GroundingSteps.to_str()}.
- Otherwise, write "None".

Answer:
- IF Grounding is required, write high-quality compelling queries (in {request.language}) for semantic or web search — no explanations.
- If Confidence >= {CONFIDENCE_THRESHOLD}, provide the complete final answer here.
- If using a tool, explain why and how the tool and its parameters are selected (only if all parameters are known).

ToolName:
Specify the exact tool name from Available Tools — or "None".

Tool Parameters:
Provide tool parameters in JSON — or "None" if no tool is needed.

Notes:
- Grounding MUST precede user clarification if factual data or uploaded resources can supply the required information.
- You may only ask the user for subjective, personal, or preference-based details — never for data retrievable by grounding.
- Always remain polite and clear.
"""
    return prompt

class StepRequest(BaseModel):
    language: str # Language of the chat
    user_intent: str  # User's intent or goal
    steps_done: List[str]  # List of steps already done
    current_step: str  # Current step to be performed
    next_steps: List[str]  # List of steps remaining to be performeds
    answer: str  # Answer to the user query

class StepResponse(BaseModel):
    final_intent: str  # Final intent of the user based on the conversation
    current_step: str  # Current step based on the predicted intent
    answer: str # Answer from the tool, if applicable
    next_steps: List[str]  # List of next steps to be performed based on the intent
    follow_up_message: str  # Follow-up message to the user to encourage further learning or exploration

class UserGroundingRequest(BaseModel):
    language: str # Language of the chat
    user_intent: str  # User's intent or goal
    queries: List[str]  # List of queries to be used for further grounding
    resources_string: str  # List of resources

class Grounding(BaseModel):
    resource: str # Resource IDs to be used for grounding
    grounding_queries: List[str]  # List of queries to be used for further grounding

class UserGroundingResponse(BaseModel):
    grounding: List[Grounding]
    reasoning: str

def user_resources_grounding_prompt(request: UserGroundingRequest) -> str:
    """
    Generates a prompt for the LLM to answer a request or require further grounding
    """
    prompt = f"""Role: You are an expert knowledge finder, your task is to determine which are the best resources to look into to fulfill an intent.
Input:
User Language: {request.language}
User Intent: {request.user_intent}
Current Date: {datetime.now().strftime("%Y-%m-%d")}
{request.resources_string}

Tasks Output Format:
Grounding: List[(str, List[str])] that contains:
    Resource: ID of one of the best resources to look into to fulfill the intent.
    Queries: Set of vector search atomic queries (in {request.language}) to be used for further grounding on the selected resource.
Reasoning: explain (in {request.language}) the reasoning behind your choice of resources.
Notes: 
Some provided resources may not be useful, in that case, simply do not use them. If no resource is useful the reasoning should explain why and the list of resources should be empty.
If you think it's extremely useful, you can ask the same question to more than one document.
Generate semantic search queries that are atomic and minimal, using only the essential conceptual terms related to the actual question — not terms tied to the resource's context or title unless they are absolutely necessary to understand the query itself.
For example: if the resource is about a system called NESON that manages calls, and the question is about how it handles memory, do NOT include terms like 'NESON' or 'calls' in the query, because these terms are already pervasive in the document and will bias vector search toward irrelevant general sections like the title or introduction.
Instead, focus purely on the real informational need — in this case: use terms like 'memory handling', 'memory allocation', 'memory management', 'caching', 'resource usage' — and omit any context-specific proper nouns unless they are essential to the meaning of the query.
Queries must be phrased to capture what needs to be retrieved, not what the document is about overall."""
    return prompt

class OERsGroundingResponse(BaseModel):
    queries: List[str]
    reasoning: str

def OERs_grounding_prompt(request: UserGroundingRequest) -> str:
    """
    Generates a prompt for the LLM to answer a request or require further grounding
    """
    prompt = f"""Role: You are an expert knowledge finder, your task is to determine which are the best questions to ask to an Open Education Resource (OER) database to fulfill an intent.
Input:
User Language: {request.language}
User Intent: {request.user_intent}

Tasks Output Format:
Queries: Set of vector search atomic queries (in {request.language}) to be used for further grounding on the OERs database.
Reasoning: explain (in {request.language}) the reasoning behind your choice of queries.
Notes: 
Generate semantic search queries that are atomic and minimal. Queries must be phrased to capture what needs to be retrieved, not general aspects a document might be about overall. Generate only necessary queries."""
    return prompt



def web_grounding_prompt(request: UserGroundingRequest) -> str:
    """
    Generates a prompt for the LLM to answer a request or require further grounding
    """
    prompt = f"""Role: You are an expert knowledge finder, your task is to determine which are the best queries to surf the web to fulfill an intent.
Input:
User Language: {request.language}
User Intent: {request.user_intent}

Tasks Output Format:
Queries: Set of vector search atomic queries (in {request.language}) to be used for further grounding on the OERs database.
Reasoning: explain (in {request.language}) the reasoning behind your choice of queries.
Notes: 
Generate web search queries that are atomic and minimal. Queries must be phrased to capture what needs to be retrieved, not general aspects a website might be about overall. Generate only necessary queries."""
    return prompt

class WebGroundingResponse(BaseModel):
    title: str
    url: str
    summary: str

class WebSearchResults(BaseModel):
    selected_websites: List[WebGroundingResponse]
    reasoning: str

def websites_selection_prompt(websites: str, intent: str, reasoning: str, language: str) -> str:
    """
    Generates a refined prompt for the LLM to select the most relevant websites based on user intent.
    """
    prompt = f"""You are an expert information curator. Your task is to select the most relevant websites from the provided list that best satisfy the user's intent and request.

### Input:
- Language: {language}
- User Intent: {intent}
- LLM Reasoning Behind Search: {reasoning}
- Websites: {websites}

### Output Requirements:
Respond with the following two sections in JSON format:

1. **SelectedWebsites**: A list (maximum 4 items) of dictionaries. Each dictionary must include:
    - "Title": Title of the website.
    - "URL": URL of the website.
    - "Summary": The query associated with this website (in {language}).

2. **Reasoning**: A brief explanation (in {language}) of why you selected these websites.

### Important Notes:
- Only select websites that directly help fulfill the user's intent and request.
- Do NOT include more than 4 websites.
- It's acceptable to return fewer than 4 if only a few are truly relevant.
- Your reasoning must clearly justify why these sites were chosen over the others.
"""
    return prompt


#---------------------------------------------Refining---------------------------------------------

class RefiningResponse(BaseModel):
    refined_answer: str
    reasoning: str

def refining_prompt(language: str, messages: List[Message], state: State, instructions: str, personal_info: Optional[PersonalInfo])->str:
    messages_str = "\n".join([message.to_str() for message in messages])
    state_str = state.to_str()
    prompt = f"""Role: You're an expert communicator, your task is to refine the response to the user based on the conversation so far to make it more useful and personalized.
The user sent a message, and some agents elaborated it through planning ang grounding, now you need to take the responses from other agents and refine the final response.
Input:
    Language: {language}
    Messages: {messages_str}
    Context: {state_str}
    User information: {personal_info}

Tasks Output Format:
Refined Answer (in {language}): This field should contain the final response to the user.
Reasoning (in {language}): This field should contain an overview of all the reasoning and tasks that were done before answering the question. It should be complete but concise, no more than three sentences.

Notes:
Try to match the user vibes and preferences to the final response. If some grounding information are available, please format them in a useful way to let the user understand whaere each grounded piece of responce comes from.
{instructions}"""
    return prompt

EXIT_GROUNDING_STRING = "Note that the grounding was not successful, as it didn't provide enough information to answer with confidence, please try to re-elaborate the information got so far. Start the answer with a very brief apology, then provide the answer you can give with the current information available, then tell the user you level of condience and the reason why the grounding was not successful."
