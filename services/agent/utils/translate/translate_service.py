from services.llm_integration.llm_interface import get_llm
from .translate_utils import TranslateResponse, translate_prompt

def translate(text, language="English", model=None, llm_token: str | None = None):
    llm = get_llm(model, api_key=llm_token)
    try:
        response = llm.generate_text(prompt=translate_prompt(text, language), response_model=TranslateResponse)
        
    except Exception as e:
        raise
    return response