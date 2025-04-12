from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .define_syllabus_service import syllabus
from .define_syllabus_utils import DefineSyllabusRequest, Syllabus

router = APIRouter(
    prefix="/tasks",
    tags=["plan"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/define_syllabus", response_model=Syllabus)
async def define_syllabus( request: DefineSyllabusRequest, access_key: str = Header(...) ):
    """
    Defines a syllabus based on:

    - **general_subject** _(str)_: The general broad subject of the syllabus. (for example, "History of the Roman Empire", "The geography of Europe", etc.)
    - **education_level** _(EducationLevel)_: The education level of the target audience.
    - **additional_information** _(str)_: Additional information about the syllabus. (for example specific sub-topics that should be included, specific learning outcomes, etc.)
    - **language** _(str)_: The language of the syllabus, defaults to "English".
    - **model** _(str)_: The model to use for generating the syllabus, defaults to "Gemini".

    Returns a JSON object with the following fields:

    - **general_subject** _(str)_: The general subject of the syllabus.
    - **educational_level** _(EducationLevel)_: The education level of the target audience.
    - **additional_information** _(str)_: Additional information about the syllabus.
    - **title** _(str)_: The title of the syllabus.
    - **description** _(str)_: The description of the syllabus.
    - **goals** _(List[str])_: A list with the goals of the syllabus.
    - **topics** _(List[Section])_: A list with the topics of the syllabus. Each Section is composed of:
        - **macro_topic** _(str)_: The macro topic of the section.
        - **details** _(str)_: The details of the section.
        - **learning_objectives** _(LearningObjectives)_: The learning objectives of the section:
            - **knowledge** _(str)_: The knowledge that the learner acquire during the section.
            - **skills** _(str)_: The skills that the learner acquire during the section.
            - **attitudes** _(str)_: The attitudes that the learner acquire during the section.
    - **prerequisites** _(List[str])_: A list with the prerequisites of the syllabus.
    - **language** _(str)_: The language of the syllabus, defaults to "English".
    """

    try: 
        authenticate(access_key)
        result = syllabus(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
