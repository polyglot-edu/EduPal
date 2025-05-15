from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId

#--------------------------------------------------------------------------------------------------------------------------
class Resource(BaseModel):
    title: str
    description: str

    class Config:
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    in_memory: bool = False
    resources: Optional[List[Resource]] = Field(default_factory=list)

    def resources_to_str(self) -> str:
        if not self.resources:
            return ""
        return "\n".join([f"Title: {resource.title} - Description: {resource.description}"
                         for resource in self.resources])

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

class Memory(BaseModel):
    key_insights: List[str] = Field(default_factory=list)
    important_facts: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""

    def to_str(self) -> str:
        insights = "\n- ".join(self.key_insights) if self.key_insights else "None"
        facts = "\n- ".join([f"{k}: {v}" for k, v in self.important_facts.items()]) if self.important_facts else "None"
        return f"Key Insights:\n- {insights}\n\nImportant Facts:\n- {facts}\n\nSummary:\n{self.summary}"

class ChatDocument(BaseModel):
    document_type: str = "chat"
    chat_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    recent_messages: List[Message] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)
    memory: Memory = Field(default_factory=Memory)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

class ChatDocumentSimplified(BaseModel):
    chat_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

#--------------------------------------------------------------------------------------------------------------------------
# Create a request model for chat creation
class ChatCreateRequest(BaseModel):
    chat_name: str

class UpdateMemoryRequest(BaseModel):
    ltm_length: int = 1207
    messages: List[Message] = Field(default_factory=list)
    memory: Memory = Field(default_factory=Memory)
    model: Optional[str] = "GEMINI"

def update_memory_prompt(request: UpdateMemoryRequest) -> str:
    messages_text = "\n".join(
        [f"{msg.role.upper()}: {msg.content}" +
         (f"\nResources:\n{msg.resources_to_str()}" if msg.resources else "")
         for msg in request.messages]
    )

    return f"""You are an AI assistant helping to maintain long-term memory for a conversation between a user and an assistant.
    Below are recent messages from the conversation. Based on these, update the memory fields as follows:
    - key_insights: high-level takeaways, goals, or behavioral patterns from the conversation
    - important_facts: structured factual information (dates, preferences, names, entities, etc.)
    - summary: a concise and clear natural-language summary of the recent exchange

    IMPORTANT:
    - Be concise and organized. Group similar facts where possible.
    - Keep important information from existing memory.
    - Ensure the values of the fields are in the same language as the messages and of the existing memory.

    EXISTING MEMORY:
    {request.memory.to_str()}

    RECENT MESSAGES:
    {messages_text}
    """