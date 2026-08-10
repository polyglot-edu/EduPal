import os
from typing import Optional
from fastapi import APIRouter, FastAPI, HTTPException, Header, File, Form, UploadFile
from common.auth import authenticate
from .analyse_material_service import analysis
from .analyse_material_utils import AnalyseMaterialResponse
import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tasks",
    tags=["material"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/analyse_material", response_model=AnalyseMaterialResponse)
async def analyse_material(
    file: Optional[UploadFile] = File(None), url: Optional[str] = Form(None), model: str = Form(...), access_key: str = Header(...), llm_token: str | None = Header(None, alias="llm_token")
):
    """
    Analyse a material and extract meaningful information. It's based on:

    - **file** _(str)_: The file to analyse.
    - **url** _(str)_: The URL of the file to analyse.
    - **model** _(str)_: The model to use for the analysis, default is "Gemini".

    NB: please upload either a file or an url; if both are uploaded, only the file will be considered

    Returns a JSON object with the following fields:

    - **language** _(str)_: The language of the material
    - **macro_subject** _(str)_: The macro subject of the material
    - **title** _(str)_: The title of the material
    - **education_level** _(str)_: The education level of the material
    - **learning_outcome** _(str)_: The learning outcome of the material
    - **topics** _(list[Topic])_: The topics of the material. Each topic is a list of:
        - **topic** _(str)_: The name of the topic
        - **explanation** _(str)_: The explanation of the topic
    - **keywords** _(list[str])_: The keywords of the material
    - **prerequisites** _(list[str])_: The prerequisites of the material
    - **estimated_duration** _(int)_: The estimated duration in minutes required to read and understand the generated material
    """

    try: 
        authenticate(access_key)

        result = await analysis(file=file, url=url, model=model, llm_token=llm_token)

        # 1.1 Delete the temp_file
        if file is not None and file.filename != "":
            from services.agent.orchestrator.chat.upload_service import TEMP_FOLDER, delete_temp_file
            url = os.path.join(TEMP_FOLDER, file.filename)
            deleted = await delete_temp_file(url)
            if deleted:
                logger.info(f"Deleted temp file: {url}")
                #print(f"Deleted temp file: {url}")

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
