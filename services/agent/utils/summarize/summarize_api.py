from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .summarize_serivce import summary
from .summarize_utils import SummarizeRequest, SummarizeResponse

router = APIRouter(
    prefix="/tasks",
    tags=["material"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_text( request: SummarizeRequest, access_key: str = Header(...) ):
    """
    Summarize a text using the specified model and style.

    - **text** _(str)_: The text to summarize.
    - **model** _(str)_: The model to use for summarization, defaults to Gemini.
    - **style** _(TextStyle)_: The style of the summary. (optional, default: Standard)
    - **education_level** _(EducationLevel)_: The education level of the audience. (optional, default: High School)
    - **learning_outcome** _(LearningOutcome)_: The learning outcome of the audience. (optional, default: Declarative)
 
    Returns a JSON object containing:

    - **summary** _(str)_: The summarized text.
    - **keywords** _(list[str])_: A list of keywords relevant to the topic.
    """
    try: 
        authenticate(access_key)

        if len(request.text) < 200:
            raise HTTPException(status_code=400, detail="Text must be at least 200 characters.")
        
        result = summary(request.text, request.model, request.style.value, request.education_level.value, request.learning_outcome.value)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
