from .translate_utils import TranslateResponse, translate_prompt
from ...llm_integration.gemini import GeminiLLM

def translate(text, language="English", model=None):
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    try:
        response = llm.generate_json(prompt=translate_prompt(text, language), response_model=TranslateResponse)
        
    except Exception as e:
        print(f"Error during translation: {e}")
        raise
    return response