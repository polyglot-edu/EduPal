from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId

from services.auth.auth_utils import PersonalInfo

#--------------------------------------------------------------------------------------------------------------------------
class Resource(BaseModel):
    id: ObjectId
    title: str
    description: str

    def to_str(self) -> str:
        return "\n".join([
            f"title: {self.title}",
            f"description: {self.description}"
        ])
    
    class Config:
        arbitrary_types_allowed = True

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    in_memory: bool = False
    resources: Optional[List[Resource]] = Field(default_factory=list)

    def to_str(self) -> str:
        items = [
            ("role", self.role),
            ("content", self.content),
            ("resources", [r.to_str() for r in self.resources] if self.resources else None)
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

class Memory(BaseModel):
    key_insights: List[str]
    important_facts: List[FactItem]
    summary: str

    class Config:
        # Allow population by field name
        populate_by_name = True

    def __init__(self, **data):
        # Set default values if not provided in data
        if 'key_insights' not in data:
            data['key_insights'] = []
        if 'important_facts' not in data:
            data['important_facts'] = []
        if 'summary' not in data:
            data['summary'] = ""

        # Call parent's __init__ with the data
        super().__init__(**data)

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
    personal_info: str = ""
    model: Optional[str] = "GEMINI"


class UpdateMemoryResponse(BaseModel):
    memory: Memory
    personal_info: Optional[PersonalInfo]

def update_memory_prompt(request: UpdateMemoryRequest) -> str:
    messages_text = "\n".join(
        [f"{msg.role.upper()}: {msg.content}" +
         (f"\nResources:\n{msg.resources_to_str()}" if msg.resources else "")
         for msg in request.messages]
    )

    return f"""You are an AI assistant helping to maintain long-term memory for a conversation between a user and an assistant.
    Below are recent messages from the conversation. Based on these, update the memory fields as follows:
    Memory fields:
        - key_insights: high-level takeaways, goals, or behavioral patterns from the conversation
        - important_facts: useful structured factual information mentioned (dates, preferences, names, entities, etc.)
        - summary: a comprehensive, concise and clear natural-language summary of the recent exchange

    IMPORTANT:
    - Be organized. Group similar information where possible.
    - Keep important information from existing memory.
    - Ensure the values of the fields are in the same language as the messages and of the existing memory.

    EXISTING MEMORY:
    {request.memory.to_str()}

    RECENT MESSAGES:
    {messages_text}

    CURRENT PERSONAL INFORMATION:
    {request.personal_info}

    Now, considering the current personal information about the user, understand if they can be updated using the new information from the messages and the memory:
    Personal information fields:
        - role: user's role (always keep the same as the existing memory)
        - name: user's name
        - age: user's age
        - location: user's location
        - occupation: user's occupation
        - interests: user's interests
        - educational_level: user's educational level (only possible levels are: "elementary school", "middle school", "high school", "college", "graduate", "professional")
    If in the messages there is some useful new information, return the updated personal_info, otherwise return None for the personal_info field. 
    """