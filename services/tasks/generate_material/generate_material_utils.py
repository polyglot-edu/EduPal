from pydantic import BaseModel
from ..common_enums import EducationLevel, LearningOutcome
from ..plan_lesson.plan_lesson_utils import Topic
from pydantic import BaseModel

class LessonNode(BaseModel):
    title: str
    learning_outcome: LearningOutcome
    topics: list[Topic]

    def toStr(self):
        return f"{self.title} ({self.learning_outcome.value}): {'\n\n- '.join([f"{topic.topic} - {topic.explanation};" for topic in self.topics])}"

class GenerateMaterialRequest(BaseModel):
    title: str
    macro_subject: str
    topics: list[LessonNode]
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    duration: int
    language: str = "English"
    model: str = "Gemini"

class GenerateMaterialResponse(BaseModel):
    material: str

class Material(BaseModel):
    title: str
    macro_subject: str
    topics: list[LessonNode]
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    duration: int
    material: str
    language: str = "English"

def generate_material_prompt(request: GenerateMaterialRequest):
   prompt = f"""You are an {request.language} expert educator and instructional designer specialized in {request.macro_subject}. 
Your expertise lies in creating **structured, engaging, and pedagogically sound lesson material**. 

### Task
Generate an explanatory text for the macro_topic: **'{request.title}'**, ensuring it aligns with best teaching practices for a **{request.education_level.value}** audience.  
The **main goal** is to help the audience achieve: **'{request.learning_outcome.value}'** on the general topic.

### Material Structure
Since you are highly organized, you will follow a structured approach to lesson planning. You have already defined the topics you want to cover and also the desired learning outcome for each topic.
These are the ordered topics you will cover:
{",\n".join([f"- {topic.toStr()}" for topic in request.topics])}

Now you can generate the material (in {request.language}), considering that it should be fully explainable in approximate {request.duration} minutes.
Remember to use appropriate vocabulary and complexity for a {request.education_level.value} audience and to adjust the depth of the topics acccordingly to the desired learning outcome.
"""
   return prompt

"""Test text:
{
  "title": "L'impero Romano",
  "macro_subject": "Storia",
  "topics": [
    {
      "title": "Le origini di Roma",
      "learning_outcome": "the ability to recall or recognize simple facts and definitions",
      "topics": [
        {
          "topic": "La leggenda di Romolo e Remo",
          "explanation": "Secondo la leggenda, Roma fu fondata da Romolo, che uccise suo fratello Remo dopo una disputa."
        },
        {
          "topic": "La fondazione di Roma",
          "explanation": "Si dice che Roma fu fondata nel 753 a.C. ed ebbe origine come un piccolo villaggio sul fiume Tevere."
        }
      ]
    },
    {
      "title": "La vita nell'antica Roma",
      "learning_outcome": "the ability to recall or recognize simple facts and definitions",
      "topics": [
        {
          "topic": "Le case romane",
          "explanation": "I ricchi vivevano in domus, case grandi e decorate; i poveri vivevano in insulae, edifici affollati."
        },
        {
          "topic": "Il cibo dei romani",
          "explanation": "I romani mangiavano pane, olive, formaggio e frutta; i più ricchi potevano permettersi piatti più elaborati."
        },
        {
          "topic": "I giochi e il tempo libero",
          "explanation": "I bambini giocavano con trottole e bambole, mentre gli adulti assistevano a spettacoli nel Colosseo."
        }
      ]
    }
  ],
  "education_level": "elementary school",
  "learning_outcome": "the ability to recall or recognize simple facts and definitions",
  "duration": 100,
  "language": "English",
  "model": "gemini"
}
"""

