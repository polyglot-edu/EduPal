from google import genai
from dotenv import load_dotenv
from .ground_utils import GroundRequest, GroundResponse, Ground, ground_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def Ground(request: GroundRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: GroundResponse = llm.generate_json(prompt=ground_prompt(request), response_model=GroundResponse)
        
        final = Ground(
            context=response.context,
        )

    except Exception as e:
        raise

    return final