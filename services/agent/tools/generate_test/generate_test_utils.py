from typing import Optional, Union
from fastapi import UploadFile
from pydantic import BaseModel, Field

from services.agent.orchestrator.chat.chat_utils import Resource
from services.agent.tools.generate_activity.generate_activity_utils import ActivityParams
from ...utils.common_enums import EducationLevel, LearningOutcome

class TopicParams(BaseModel):
    topic_name: str
    topic_explanation: str
    learning_outcome: LearningOutcome = LearningOutcome.UNDERSTANDING
    exercise_params: list[ActivityParams] = Field(default_factory=list)
    
class GenerateTestRequest(BaseModel):
    macro_subject: str
    education_level: EducationLevel
    topics: list[TopicParams] = Field(default_factory=list)
    material: Optional[Union[UploadFile, list[Resource]]] = None
    learning_outcome: LearningOutcome = LearningOutcome.UNDERSTANDING
    exercises: list[ActivityParams] = Field(default_factory=list)
    language: str = "English"
    model: str = "default"
 
"""Test text:
{
  "macro_subject": "Storia",
  "education_level": "middle school",
  "topics": [
    {
      "topic_name": "Le Origini e la Monarchia (753–509 a.C.)",
      "topic_explanation": "Roma fu fondata, secondo la leggenda, da Romolo nel 753 a.C. Durante questo periodo, Roma fu governata da una serie di sette re. Fu un’epoca di formazione istituzionale, con la nascita del Senato e delle prime strutture sociali e religiose.",
      "learning_outcome": "the ability to explain concepts and principles, and recognize how different ideas are related",
      "exercise_params": [
        {
          "type": "multiple choice",
          "solutions_number": 1,
          "distractors_number": 2,
          "easily_discardable_distractors_number": 3
        },
        {
          "type": "multiple select",
          "solutions_number": 3,
          "distractors_number": 2,
          "easily_discardable_distractors_number": 2
        }
      ]
    },
    {
      "topic_name": "La Repubblica Romana (509–27 a.C.)",
      "topic_explanation": "Dopo la cacciata dell’ultimo re, Tarquinio il Superbo, Roma divenne una repubblica. Il potere era nelle mani del Senato e dei magistrati eletti. Roma espanse il proprio controllo su tutta l’Italia e poi nel Mediterraneo, affrontando nemici come Cartagine nelle guerre puniche.",
      "learning_outcome": "the ability to explain concepts and principles, and recognize how different ideas are related",
      "exercise_params": []
    },
    {
      "topic_name": "La Crisi della Repubblica e le Guerre Civili (133–27 a.C.)",
      "topic_explanation": "Conflitti interni, disuguaglianze economiche e lotte per il potere portarono al declino della Repubblica. Figure come Mario, Silla, Pompeo, Cesare e infine Ottaviano segnarono una fase di transizione turbolenta verso un nuovo sistema di governo.",
      "learning_outcome": "the ability to explain concepts and principles, and recognize how different ideas are related",
      "exercise_params": [
        {
          "type": "open question",
          "solutions_number": 1,
          "distractors_number": 2,
          "easily_discardable_distractors_number": 3
        }
      ]
    }
  ],
  "material": [],
  "learning_outcome": "the ability to explain concepts and principles, and recognize how different ideas are related",
  "exercises": [],
  "language": "Italian",
  "model": "Gemini"
}
"""

