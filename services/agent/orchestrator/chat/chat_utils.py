from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from bson import ObjectId

from services.auth.auth_utils import PersonalInfo
from services.agent.grounding.analyse_material.analyse_material_utils import Analysis


LTM_LENGTH = 1207  # Default length of long-term memory in tokens

#--------------------------------------------------------------------------------------------------------------------------

class Resource(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    document_type: str = "resource"
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    analysis: Analysis
    content: List[Dict[str, Any]]
    
    def to_str(self) -> str:
        return "\n".join([
            f"ID: {self.id}",
            f"title: {self.analysis.title}",
            f"keywords: {self.analysis.keywords}"
        ])
    
    class Config:
        arbitrary_types_allowed = True

class ResourceDocumentSimplified(BaseModel):
    id: str = Field(..., alias="_id")
    document_type: str = "resource"
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    analysis: Analysis

    class Config:
        arbitrary_types_allowed = True

    def to_str(self) -> str:
        return "\n".join([
            f"ID: {self.id}",
            f"title: {self.analysis.title}",
            f"keywords: {self.analysis.keywords}"
        ])

class ResourceIdsRequest(BaseModel):
    resource_ids: List[str]

class Message(BaseModel):
    content: str
    role: Optional[str] = "user"  # Default role is 'user'
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    in_memory: Optional[bool] = False
    system_instructions: Optional[str] = None
    resources: Optional[List[str]] = Field(default_factory=list)  # List of resource IDs

    def to_str(self) -> str:
        items = [
            ("role", self.role),
            ("content", self.content),
            ("system_instructions", self.system_instructions)
        ]
        lines = []
        for k, v in items:
            if v is None or v == "" or v == []:
                continue
            if isinstance(v, list):
                lines.append(f"{k}:")
                lines.extend([f"  - {line}" for line in v])
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

class FactItem(BaseModel):
    key: str
    values: List[str]

    def to_str(self, indent: str = "") -> str:
        # If there's only one value, display it directly
        if len(self.values) == 1:
            return f"{indent}{self.key}: {self.values[0]}"
        # If there are multiple values, display them as a bulleted list
        values_str = "\n".join(f"{indent}  - {value}" for value in self.values)
        return f"{indent}{self.key}:\n{values_str}"

class StructuredMemory(BaseModel):
    key_insights: List[str]
    important_facts: List[FactItem]
    summary: str

    class Config:
        # Allow population by field name
        populate_by_name = True

    def to_str(self) -> str:
        lines = []

        # Add key insights
        if self.key_insights:
            lines.append("Key Insights:")
            lines.extend([f"  - {insight}" for insight in self.key_insights])

        # Add important facts
        if self.important_facts:
            lines.append("Important Facts:")
            for fact in self.important_facts:
                lines.append(fact.to_str("  "))

        # Add summary
        if self.summary:
            lines.append("Summary:")
            lines.append(f"  {self.summary}")

        return "\n".join(lines)

    def toString() -> str:
        return f"""- key_insights: high-level takeaways, goals, or behavioral patterns from the conversation
    - important_facts: useful structured factual information mentioned (dates, preferences, names, entities, etc.)
    - summary: a comprehensive, concise and clear natural-language summary of the recent exchange"""

def default_structured_memory() -> StructuredMemory:
    return StructuredMemory(
        key_insights=[],
        important_facts=[],
        summary=""
    )

class Memory(BaseModel):
    recent_messages: List[Message] = Field(default_factory=list)
    structured_memory: StructuredMemory = Field(default_factory=default_structured_memory)

    def to_str(self) -> str:
        recent_messages_str = "\n".join(msg.to_str() for msg in self.recent_messages)
        structured_memory_str = self.structured_memory.to_str()
        return f"Recent Messages:\n{recent_messages_str}\n\nStructured Memory:\n{structured_memory_str}"

class GoalState(BaseModel):
    final_goal: str
    current_intent: str
    steps_done: List[str]
    next_steps: List[str]

    def to_str(self) -> str:
        return "\n".join([
            f"final_goal: {self.final_goal}",
            f"steps_done: {self.steps_done}",
            f"next_steps: {self.next_steps[1:] if self.next_steps else ''}", # Next steps except the first element
            f"current_intent: {self.current_intent}",
            f"current_step: {self.next_steps[0] if self.next_steps else ''}"
        ])
    
    def toString(self) -> str:
        return f"""Final Goal: Detect (if not given), edit, or confirm the user's final goal (in the detected language).
Current Intent: Considering all the information at your disposal, clearly state the user's current intent (in the detected language). Rephrase the user request to better capture the intent, the eventual explicit time references and/or resources references. Integrate all the relevant context from the chat history, memory, and user profile. Adhere to PROMPT ENGINEERING best practices, ensuring the intent is clear and actionable. If the intent is not clear, write "Intent Not Clear". If the user intent is to end the chat, write "End Chat".
Steps Done: List the steps toward the fulfillment of the user intent already done by inferring them from the chat context (in the detected language). If it's a new intent, so no steps have been done, write "None".
Next Steps: If the user query is valid and the final goal is clear, plan, edit, or confirm a list of next steps (including the current step) needed to fulfill the final goal (in the detected language), also considering (eventually) the available tools. For each step, only if applicable, add the name of the tool (by original English name) that you intend to use. The list of steps can contain even just one step (the current step) if the final goal is straightforward. 
"""
    
    def reset(self):
        self.final_goal = ""
        self.current_intent = ""
        self.steps_done = []
        self.next_steps = []
        
class GroundingState(BaseModel):
    models: List[str] = Field(default_factory=list)  # List of models used for grounding
    last_grounding_step: str = ""
    grounded_info: str = ""

    def to_str(self) -> str:
        return "\n".join([
            f"models_used: {self.models}",
            f"last_grounding_step: {self.last_grounding_step}",
            f"grounded_info: {self.grounded_info}"
        ])
    
    def toString(self) -> str:
        return f"""Models Used: List of the models used to ground the current step.
Last Grounding Step: The step of the plan that was last grounded.
Grounded Info: The information used to ground the last step."""
    
    def reset(self):
        self.models = []
        self.last_grounding_step = ""
        self.grounded_info = ""
   
def default_goal_state() -> GoalState:
        return GoalState(
            final_goal="",
            current_intent="",
            steps_done=[],
            next_steps=[]
        )

class State(BaseModel):
    goal_state: GoalState = Field(default_factory=default_goal_state)
    grounding_state: GroundingState = Field(default_factory=GroundingState)

    def to_str(self) -> str:
        return "\n".join([
            self.goal_state.to_str(),
            self.grounding_state.to_str()
        ])
    
    def reset(self):
        self.goal_state.reset()
        self.grounding_state.reset()

    def toString(self) -> str:
        return f"""{self.goal_state.toString()}\n{self.grounding_state.toString()}"""

class ChatDocument(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    document_type: str = "chat"
    chat_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    messages: List[Message] = Field(default_factory=list)
    memory: Memory = Field(default_factory=Memory)
    state: State = Field(default_factory=State)
    resources: list[str] = Field(default_factory=list)  # list of resource ids associated to the chat

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

class ChatDocumentSimplified(BaseModel):
    id: str = Field(..., alias="_id")
    chat_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

class UpdateChatRequest(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    state: State = Field(default_factory=State)
    model: Optional[str] = "GEMINI"
#--------------------------------------------------------------------------------------------------------------------------

# Create a request model for memory update
class ChatCreateRequest(BaseModel):
    chat_name: str

class UpdateStructuredMemoryRequest(BaseModel):
    ltm_length: int = LTM_LENGTH
    memory: Memory = Field(default_factory=Memory)
    personal_info: str = ""
    model: Optional[str] = "GEMINI"

class UpdateStructuredMemoryResponse(BaseModel):
    structured_memory: StructuredMemory
    personal_info: Optional[PersonalInfo]

def update_structured_memory_prompt(request: UpdateStructuredMemoryRequest) -> str:
    messages_text = "\n".join(
        [f"{msg.role.upper()}: {msg.content}" +
         (f"\nResources ids:\n{msg.resources}" if msg.resources else "")
         for msg in request.memory.recent_messages]
    )

    return f"""You are a helpful assistant that is tasked with maintaining a long-term StructuredMemory for a conversation between a user and an assistant.
    Below are recent messages from the conversation. Based on these, update the StructuredMemory fields as follows:
    StructuredMemory fields:
    {StructuredMemory.toString()}
    
    IMPORTANT:
    - Be organized. Group similar information where possible.
    - For each eexisting Structured Memory information, if it's is still valid and relevant, keep it, otherwise update it or revmove it.
    - Ensure the summary is comprehensive, concise, and clear.
    - Ensure the values of the fields are in the same language of the messages and of the existing StructuredMemory.

    EXISTING MEMORY:
    {request.memory.structured_memory.to_str()}

    RECENT MESSAGES:
    {messages_text}

    CURRENT PERSONAL INFORMATION:
    {request.personal_info}

    Now, considering the current personal information about the user, understand if they can be updated using the new information from the messages and the StructuredMemory:
    Personal information fields:
    {PersonalInfo.toString()}
    If in the messages there is some useful new information, return the updated personal_info, otherwise return None for the personal_info field. 
    """

#--------------------------------------------------------------------------------------------------------------------------

# Create a request model for sending a message to the chat
class SendMessageRequest(BaseModel):
    chat_id: str
    message: Message
    memory: Memory
    state: State
    personal_info: Optional[PersonalInfo] = None
    model: str = "GEMINI"


STUDENT_SYSTEM_INSTRUCTIONS = """Your primary goal is to facilitate learning and understanding, not to provide direct answers when a student is expected to solve a problem independently (e.g., during tests, quizzes, or practice exercises).

When a student asks for the solution to a specific problem or exercise:

Do not provide the direct answer.
Instead, offer guidance, hints, or leading questions that help the student arrive at the answer themselves.
Encourage them to explain their current thinking or what they've tried so far.
Break down the problem into smaller steps if necessary.
When a student asks about a new concept, definition, or general information they genuinely don't know:

Provide clear, concise, and accurate explanations.
Offer examples to illustrate the concept.
Suggest follow-up topics for further exploration.
Answer their questions directly and comprehensively, just as a human tutor would when introducing new material."""
