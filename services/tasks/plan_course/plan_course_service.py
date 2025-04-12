from google import genai
from dotenv import load_dotenv
from .plan_course_utils import PlanCourseRequest, PlanCourseResponse, CoursePlan, plan_course_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def course_plan(request: PlanCourseRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: PlanCourseResponse = llm.generate_json(prompt=plan_course_prompt(request), response_model=PlanCourseResponse)
        #print("Response",response)
        #print("-"*50)

        final = CoursePlan(
            title=request.title,
            macro_subject=request.macro_subject,
            education_level=request.education_level,
            learning_objectives=request.learning_objectives,
            number_of_lessons=request.number_of_lessons,
            duration_of_lesson=request.duration_of_lesson,
            prerequisites=response.prerequisites,
            nodes=response.nodes,
            language=request.language
        )
   
    except Exception as e:
        raise

    return final
