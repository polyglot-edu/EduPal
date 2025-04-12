from pydantic import BaseModel
from ..common_enums import EducationLevel, LearningOutcome, TypeOfActivity, LearningObjectives
from pydantic import BaseModel
from typing import List

class Section(BaseModel):
    macro_topic: str
    details: str
    learning_objectives: LearningObjectives

class DefineSyllabusResponse(BaseModel):
    title: str
    description: str
    goals: List[str]
    topics: List[Section]
    prerequisites: List[str]

class DefineSyllabusRequest(BaseModel):
    general_subject: str
    education_level: EducationLevel
    additional_information: str
    language: str = "English"
    model: str = "Gemini"

class Syllabus(BaseModel):
    general_subject: str
    educational_level: EducationLevel
    additional_information: str
    title: str
    description: str
    goals: List[str]
    topics: List[Section]
    prerequisites: List[str]
    language: str = "English"

def define_syllabus_prompt(request: DefineSyllabusRequest):
   more = ""
   if request.additional_information is not None and request.additional_information != "":
       more = f"To improve the quality of your syllabus, here are some additional information to consider:\n{request.additional_information}\n"
   prompt = f"""You are an {request.language} expert educator and instructional designer specialized in creating **structured, engaging, and pedagogically sound syllabi**. 

### Task
Generate a **syllabus** for the general_subject: **'{request.general_subject}'**, ensuring it aligns with best teaching practices for a **{request.education_level}** audience.
{more}
### Syllabus Structure
You shall start by generating in {request.language} a captivating **title** and a **description** that clearly outlines the syllabus's purpose and scope.
Then, you will create a list of **goals** (still in {request.language}) that define the overall objectives of the syllabus. These goals should be very broad and encompass only the key macro_themes and skills to be developed throughout the course.
Since you are highly organized, you will then provide a **logical sequence of Sections** (in {request.language}) that will guide the learner through the learning of the general subject.
Each **Section** consists of:  
- **MacroTopic** (in {request.language}): The main topic of the section. Note that this macro topics should be very broad. For example, if the general subject is "History of the Roman Empire", possible macro topics could be "From the Birth of Rome to the first Republic", "The Republic of Rome", "The Roman Empire", "The Fall of the Roman Empire and its heritage", etc.
- **Details** (in {request.language}): A short description of the macro topic, providing a brief overview of the content to be covered, from where to where.
- **Learning Objectives**: 
    - Knowledge (in {request.language}): The knowledge that the learner acquire during the section.
    - Skills (in {request.language}): The skills that the learner should have at the end of the section.
    - Attitude (in {request.language}): The attitude that the learner should develop during the section.

### Prerequisites  
Now that you know how the lesson will be, list the key **prerequisites** (in {request.language}) your audience should already be familiar with (keep it concise).  
"""
   return prompt

"""Test text:
{
  "general_subject": "Geografia dell'Europa",
  "education_level": "high school",
  "additional_information": "",
  "language": "Italian",
  "model": "gemini"
}
"""

