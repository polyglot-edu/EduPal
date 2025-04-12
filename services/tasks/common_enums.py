from enum import Enum
from pydantic import BaseModel

class TextStyle(Enum):
  SYNTHETIC = "topic / synthetic"
  STANDARD = "standard descriptive"
  ABSTRACTIVE = "abstractive"
  EXTRACTIVE = "extractive"
  EXPLANATORY = "explanatory and evaluative"
  INFORMAL = "informal"
  STRUCTURED = "structured and informative"

class EducationLevel(Enum):
  ELEMENTARY = "elementary school"
  MIDDLE_SCHOOL = "middle school"
  HIGH_SCHOOL = "high school"
  COLLEGE = "college"
  GRADUATE = "graduate"
  PROFESSIONAL = "professional"

class LearningOutcome(Enum):
    DECLARATIVE = "the ability to recall or recognize simple facts and definitions"
    UNDERSTANDING = "the ability to explain concepts and principles, and recognize how different ideas are related"
    PROCEDURAL = "the ability to apply knowledge and perform operations in practical contexts"
    METACOGNITIVE = "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps"
    SCHEMATIC = "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction"
    TRANSFORMATIVE = "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"

class LearningObjectives(BaseModel):
    knowledge: str
    skills: str
    attitude: str

    def toString(self):
        return f"\nKnowledge: {self.knowledge},\nSkills: {self.skills},\nAttitude: {self.attitude}"

class TypeOfActivity(Enum):
    OPEN_QUESTION = "open question"
    SHORT_ANSWER_QUESTION = "short answer question"
    TRUE_OR_FALSE = "true or false"
    # INFORMATION_SEARCH = "information search" can be done by using the result of the fill in the blanks activity
    FILL_IN_THE_BLANKS = "fill in the blanks"
    MATCHING = "matching"  
    ORDERING = "ordering"
    MULTIPLE_CHOICE = "multiple choice"
    MULTIPLE_SELECT = "multiple select"
    CODING = "coding"
    ESSAY = "essay"
    KNOWLEDGE_EXPOSITION = "knowledge exposition"
    #TEXT_COMPREHENSION = "text comprehension"
    DEBATE = "debate"
    BRAINSTORMING = "brainstorming"
    GROUP_DISCUSSION = "group discussion"
    SIMULATION = "simulation"
    INQUIRY_BASED_LEARNING = "inquiry based learning"
    NON_WRITTEN_MATERIAL_ANALYSIS = "non written material analysis"
    NON_WRITTEN_MATERIAL_PRODUCTION = "non written material production"
    CASE_STUDY_ANALYSIS = "case study analysis"
    PROJECT_BASED_LEARNING = "project based learning"
    PROBLEM_SOLVING_ACTIVITY = "problem solving activity"    
    #CONCEPTUAL_MAPS = "conceptual maps"
    #GRAPHS = "graphs"
    #TABLES = "tables"
    #DIAGRAMS = "diagrams"
    #FLOWCHARTS = "flowcharts"
    #TIMELINES = "timelines"

class TypeOfAssessment(Enum):
    PEER_REVIEW = "peer review"
    SELF_ASSESSMENT = "self assessment"
    TEACHER_ASSESSMENT = "teacher assessment"
    AUTOMATED_ASSESSMENT = "automated assessment"
