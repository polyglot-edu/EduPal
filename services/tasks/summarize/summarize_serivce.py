from google import genai
from dotenv import load_dotenv
from .summarize_utils import SummarizeResponse, summarize_prompt
from ..common_enums import TextStyle, EducationLevel, LearningOutcome
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def summary(text, model=None, style=TextStyle.STANDARD, education_level=EducationLevel.HIGH_SCHOOL, learning_outcome=LearningOutcome.DECLARATIVE):
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response = llm.generate_json(prompt=summarize_prompt(text, style, education_level, learning_outcome), response_model=SummarizeResponse)
    except Exception as e:
        print(f"Error during summarization: {e}")
        raise
    return response