from google import genai
from dotenv import load_dotenv
from .define_syllabus_utils import DefineSyllabusRequest, DefineSyllabusResponse, Syllabus, define_syllabus_prompt
from ...llm_integration.gemini import GeminiLLM
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

def syllabus(request: DefineSyllabusRequest):
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response: DefineSyllabusResponse = llm.generate_json(prompt=define_syllabus_prompt(request), response_model=DefineSyllabusResponse)
        #print("Response",response)
        #print("-"*50)

        final = Syllabus(
            general_subject=request.general_subject,
            educational_level=request.education_level,
            additional_information=request.additional_information,
            title=response.title,
            description=response.description,
            goals=response.goals,
            topics=response.topics,
            prerequisites=response.prerequisites,
            language=request.language
        )
   
    except Exception as e:
        raise

    return final
