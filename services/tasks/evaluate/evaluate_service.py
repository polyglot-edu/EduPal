from google import genai
from dotenv import load_dotenv
from .evaluate_utils import EvaluateRequest, EvaluateResponse, Evaluation, evaluate_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def evaluation(request: EvaluateRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        #print("Prompt: ",evaluate_prompt(request))
        #print("-"*100)
        #print("\n\n\n")
        response: EvaluateResponse = llm.generate_json(prompt=evaluate_prompt(request), response_model=EvaluateResponse)
        print("Response",response)
        print("-"*100)

        final = Evaluation(
            macro_subject=request.macro_subject,
            topic=request.topic,
            education_level=request.education_level,
            learning_outcome=request.learning_outcome,
            assignment=request.assignment,
            answer=request.answer,
            solutions=request.solutions,
            correctness_percentage=response.correctness_percentage,
            comment=response.comment,
            advice=response.advice,
            type=request.type,
            language=request.language,
        )

    except Exception as e:
        raise

    return final