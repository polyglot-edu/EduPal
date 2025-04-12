from google import genai
from dotenv import load_dotenv
from .generate_activity_utils import GenerateActivityRequest, GenerateActivityResponse, Activity, generate_activity_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def activity(request: GenerateActivityRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        #print("Prompt: ",generate_activity_prompt(request))
        #print("-"*100)
        #print("\n\n\n")
        response: GenerateActivityResponse = llm.generate_json(prompt=generate_activity_prompt(request), response_model=GenerateActivityResponse)
        print("Response",response)
        print("-"*100)

        final = Activity(
            macro_subject=request.macro_subject,
            topic=request.topic,
            education_level=request.education_level,
            learning_outcome=request.learning_outcome,
            material=request.material,
            assignment=response.assignment,
            plus=response.plus,
            solutions=response.solutions,
            distractors=response.distractors,
            easily_discardable_distractors=response.easily_discardable_distractors,
            type=request.type,
            language=request.language,
        )

    except Exception as e:
        raise

    return final