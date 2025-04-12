from google import genai
from dotenv import load_dotenv
from .plan_lesson_utils import PlanLessonRequest, PlanLessonResponse, LessonPlan, plan_lesson_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def lesson_plan(request: PlanLessonRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: PlanLessonResponse = llm.generate_json(prompt=plan_lesson_prompt(request), response_model=PlanLessonResponse)
        
        final = LessonPlan(
            title=request.title,
            macro_subject=request.macro_subject,
            education_level=request.education_level,
            learning_outcome=request.learning_outcome,
            prerequisites=response.prerequisites,
            nodes=response.nodes,
            context=request.context,
            language=request.language
        )

    except Exception as e:
        raise

    return final
