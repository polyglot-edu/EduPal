from services.llm_integration.llm_interface import get_llm
from .define_syllabus_utils import DefineSyllabusRequest, DefineSyllabusResponse, Syllabus, define_syllabus_prompt

def syllabus(request: DefineSyllabusRequest, llm_token: str | None = None):
    llm = get_llm(request.model, api_key=llm_token)
    try:
        response: DefineSyllabusResponse = llm.generate_text(prompt=define_syllabus_prompt(request), response_model=DefineSyllabusResponse)
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
