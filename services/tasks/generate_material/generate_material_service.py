from google import genai
from dotenv import load_dotenv
from .generate_material_utils import GenerateMaterialRequest, GenerateMaterialResponse, Material, generate_material_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def material(request: GenerateMaterialRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        #print("Prompt: ",generate_material_prompt(request))
        #print("-"*100)
        #print("\n\n\n")
        response: GenerateMaterialResponse = llm.generate_json(prompt=generate_material_prompt(request), response_model=GenerateMaterialResponse)
        #print("Response",response)
        #print("-"*100)

        final = Material(
            title=request.title,
            macro_subject=request.macro_subject,
            topics=request.topics,
            education_level=request.education_level,
            learning_outcome=request.learning_outcome,
            duration=request.duration,
            material=response.material,
            language=request.language,
        )

    except Exception as e:
        raise

    return final