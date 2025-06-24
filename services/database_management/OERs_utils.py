from typing import List, Optional

from pydantic import BaseModel

from services.agent.utils.common_enums import EducationLevel


class UploadResponse(BaseModel):
    success: bool
    message: str

class UploadRequest(BaseModel):
    resources_ids: List[str] 

class DeleteRequest(BaseModel):
    collection_name: str
    resources_ids: List[str]
    

class Filters(BaseModel):
    collection_name: str
    title: Optional[str] = None
    description: Optional[str] = None
    educational_level: Optional[EducationLevel] = None

class GetResourceRequest(BaseModel):
    collection_name: str
    resource_id: str
