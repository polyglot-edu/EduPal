from google import genai
from dotenv import load_dotenv
from .refine_utils import RefineRequest, Refinement, refine_prompt
from services.llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def refinement(request: RefineRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        #print("Prompt: ",refine_prompt(request))
        #print("-"*100)
        #print("\n\n\n")
        response: Refinement = llm.generate_text(prompt=refine_prompt(request), response_model=Refinement)
        #print("Response",response)
        #print("-"*100)

        final = Refinement(
            refined_json=response.refined_json
        )

    except Exception as e:
        raise

    return final