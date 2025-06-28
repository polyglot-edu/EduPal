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

    def toString()-> str:
        return "'elementary school', 'middle school', 'high school', 'college', 'graduate', 'professional'"

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

class ActionType(Enum):
    GENERATE_SYLLABUS = "GenerateSyllabus"
    TRANSLATE_TEXT = "TranslateText"
    SUMMARIZE_TEXT = "SummarizeText"
    GENERATE_MATERIAL = "GenerateMaterial"
    GENERATE_ACTIVITY = "GenerateActivity"
    EVALUATE_ACTIVITY = "EvaluateActivity"
    PLAN_COURSE = "PlanCourse"
    PLAN_LESSON = "PlanLesson"

def sanitize_enums(data: dict, enum_fields: dict) -> dict:
    def _get_nested(d, keys):
        for k in keys[:-1]:
            d = d.get(k, {})
        return d

    for path, enum_cls in enum_fields.items():
        keys = path.split(".")
        target_dict = _get_nested(data, keys)
        last_key = keys[-1]
        
        if isinstance(target_dict, dict):
            raw_value = target_dict.get(last_key)
            if isinstance(raw_value, str):
                resolved = resolve_enum(enum_cls, raw_value)
                if resolved:
                    target_dict[last_key] = resolved

    return data


def resolve_enum(enum_class: type[Enum], key: str) -> str | None:
    """Resolve an enum value from a key, safely (case-insensitive)."""
    if not isinstance(key, str):
        return None
    try:
        return enum_class[key.upper()].value
    except KeyError:
        return None
