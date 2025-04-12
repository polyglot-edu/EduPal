from google import genai
from dotenv import load_dotenv
from .analyse_material_utils import AnalyseMaterialRequest, AnalyseMaterialResponse, Analysis, analyse_material_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def analysis(request: AnalyseMaterialRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: AnalyseMaterialResponse = llm.generate_json(prompt=analyse_material_prompt(request), response_model=AnalyseMaterialResponse)
        
        final = Analysis(
            language=response.language,
            macro_subject=response.macro_subject,
            title=response.title,
            education_level=response.education_level,
            learning_outcome=response.learning_outcome,
            topics=response.topics,
            keywords=response.keywords,
            prerequisites=response.prerequisites,
            estimated_duration=response.estimated_duration,
        )

    except Exception as e:
        raise

    return final