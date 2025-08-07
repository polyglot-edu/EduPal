from services.llm_integration.llm_interface import get_llm
from .summarize_utils import SummarizeResponse, summarize_prompt
from ..common_enums import TextStyle, EducationLevel, LearningOutcome

def summary(text, model=None, style=TextStyle.STANDARD, education_level=EducationLevel.HIGH_SCHOOL, learning_outcome=LearningOutcome.DECLARATIVE):
    llm = get_llm(model)
    try:
        response = llm.generate_text(prompt=summarize_prompt(text, style, education_level, learning_outcome), response_model=SummarizeResponse)
    except Exception as e:
        #print(f"Error during summarization: {e}")
        raise
    return response