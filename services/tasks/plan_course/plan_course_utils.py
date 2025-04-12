from pydantic import BaseModel
from ..common_enums import EducationLevel, LearningOutcome, LearningObjectives
from ..plan_lesson.plan_lesson_utils import Topic
from pydantic import BaseModel
from typing import List

class LessonNode(BaseModel):
    title: str
    learning_outcome: LearningOutcome
    topics: list[Topic]

class PlanCourseRequest(BaseModel):
    title: str
    macro_subject: str
    education_level: EducationLevel
    learning_objectives: LearningObjectives
    number_of_lessons: int
    duration_of_lesson: int
    language: str = "English"
    model: str = "Gemini"

class PlanCourseResponse(BaseModel):
    prerequisites: List[str]
    nodes: List[LessonNode]

class CoursePlan(BaseModel):
    title: str
    macro_subject: str
    education_level: EducationLevel
    learning_objectives: LearningObjectives
    number_of_lessons: int
    duration_of_lesson: int
    prerequisites: List[str]
    nodes: List[LessonNode]
    language: str = "English"


def plan_course_prompt(request: PlanCourseRequest):
   prompt = f"""You are an expert {request.language} educator and instructional designer specialized in {request.macro_subject}. 
Your expertise lies in creating **structured, engaging, and pedagogically sound course plans**. 

### Task
Generate a **comprehensive course plan** for the macro_topic: **'{request.title}'**, ensuring it aligns with best teaching practices for a **{request.education_level.value}** audience.  
The **main goal** is to help the audience achieve the following learning outcomes: '{request.learning_objectives.toString()}'.

### Course Plan Structure
Since you are highly organized, you will structure the course as a **logical sequence of {request.number_of_lessons} lessons**.
Each **lesson** consists of:
- **Title** (in {request.language}): the general topic of the lesson, 
- **Learning Outcome** (in English from the list): desired learning outcome for the main topic of the lesson. (Note that not all the lessons will be about an equally important topic, so balance the learning outcomes accordingly.)
- **Topics**: the specific topics covered in the lesson, each topic is composed of:
    - **Topic** (in {request.language}): Title of the specific topic.
    - **Explanation** (in {request.language}): More detailed description of the topic.

  Here are the available **Learning Outcome** options:
  {", ".join(e.value for e in LearningOutcome)}

Each of the {request.number_of_lessons} lessons should have an approximate duration of {request.duration_of_lesson} minutes, so adjust the number and difficulty of the topics acccordingly.

### Prerequisites  
Now that you know how the course will be, list the key **prerequisites** (in {request.language}) your audience should already be familiar with (keep it concise).  
"""
   return prompt

"""Test text:
{
  "title": "The Roman Empire",
  "macro_subject": "History",
  "education_level": "elementary school",
  "learning_outcome": "the ability to recall or recognize simple facts and definitions",
  "number_of_lessons": 11,
  "duration_of_lesson": 60,
  "language": "spanish",
  "model": "gemini"
}
"""

