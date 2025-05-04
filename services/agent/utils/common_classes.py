from pydantic import BaseModel
from enum import Enum
from .common_enums import ActionType

class ActionData(BaseModel):
    action: str
    type: ActionType
    description: str
    input: dict
    output: dict
    dependencies: list
    status: str
    metadata: dict
  
  
"""
  "input": {
    "required_data": ["text", "language"],  // dynamic based on action type
    "context": {
      "user_goal": "...",
      "user_level": "...",
      "subject": "...",
      "constraints": ["..."]
    }
  },
  "output": {
    "expected_result": "What the action should return or change",
    "format": "text | json | pdf | suggestion_list | ...",
    "store_result": true
  },
  "dependencies": ["action_id_1", "action_id_2"],  // actions this one depends on
  "status": "pending | running | completed | failed",
  "metadata": {
    "created_at": "...",
    "executed_by": "agent_name | user",
    "estimated_time": "..."
  }
"""
