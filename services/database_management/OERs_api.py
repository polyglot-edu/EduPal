from typing import List
from bson import ObjectId
from click import Tuple
from fastapi import APIRouter, HTTPException, status, Header, Body
import os
from motor.motor_asyncio import AsyncIOMotorClient
import logging
logger = logging.getLogger(__name__)

from common.auth import authenticate_user as authenticate
from services.agent.grounding.vector_search_retrieval.vector_search_service import find_resources_from_queries, pair_queries_with_collection, query_documents_with_filter
from services.agent.orchestrator.chat.chat_service import get_complete_resources_by_ids
from services.agent.orchestrator.chat.chat_utils import Resource, ResourceDocumentSimplified
from services.agent.orchestrator.orchestrator.agent_utils import Grounding
from services.auth.auth_service import create_search_index, get_profile, validate_token
from services.auth.auth_utils import UserProfileDocument
from services.database_management.OERs_utils import DeleteRequest, Filters, GetResourceRequest, UploadRequest, UploadResponse
# Constants
SECRET_KEY = os.getenv("USERS_SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # MongoDB URI

# MongoDB connection - using async client
DB_NAME = "OERs"
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
user_db = client["user_data"]
SIMILARITY_THRSHOLD = float(os.getenv("SIMILARITY_THRSHOLD", "0.75"))  # Default threshold for similarity
SCORE_THRESHOLD = 0.55

# Endpoints
router = APIRouter(
    prefix="/oers",
    tags=["database_operations"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)


@router.post("/upload-to-oerdb", response_model=UploadResponse)
async def upload_to_oerdb(request: UploadRequest = Body(...), token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key") ):
    """
    Upload OERs to the database.
    - **request**: UploadRequest containing the resources ids to upload
    - **token**: JWT token for user authentication
    - **access_key**: Access key for API authentication

    This endpoint allows teachers to upload OERs to the database.
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        username, _, _ = await validate_token(user_db, token, SECRET_KEY, ALGORITHM)
        print(f"Authenticated user: {username}")
        # Get user's personal collection
        user_collection = user_db[username]

        # Get user's profile document
        profile: UserProfileDocument = await get_profile(user_collection)
        user_profile = UserProfileDocument(**profile)

        role = user_profile.personal_info.role

        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        if role != "teacher" and role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only teachers or admins can upload OERs"
            )
        
        print(request.resources_ids)
        # Retrieve the resource
        resources: List[Resource] = await get_complete_resources_by_ids(user_collection, request.resources_ids)
        if not resources:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resources not found"
            )
        
        print(f"resources type: {type(resources)}")

        queries = [resource.analysis.macro_subject for resource in resources]
        print(f"Queries: {queries}")
        collections: List[str] = await db.list_collection_names()
        print(f"Collections: {collections}")
        
        # Get the matching collection from the OERs database
        pairs = pair_queries_with_collection(
            queries=[resource.analysis.macro_subject for resource in resources],
            collections=collections
        )

        print(f"User profile: {role}")

        for idx, (query, best_collection, similarity_score) in enumerate(pairs):
            resource = resources[idx]
            resource_id = resource.id
            resource_data = resource.model_dump()
            print(f"Resource data: {resource_id}")
            resource_data["_id"] = ObjectId(resource_id)
            analysis =resource_data["analysis"]
            analysis["education_level"] = resource.analysis.education_level.value
            analysis["learning_outcome"] = resource.analysis.learning_outcome.value
            resource_data["analysis"] = analysis

            # Delete id field
            del resource_data["id"]

            print(f"Similarity score: {similarity_score}")
            print(f"Similarity threshold: {SIMILARITY_THRSHOLD}")
            if similarity_score > SIMILARITY_THRSHOLD:
                # Use the matched collection
                collection = db[best_collection]
                print("similarity is high enough, using existing collection")
                # Check if resource already exists (assuming uniqueness by "_id")
                existing = await collection.find_one({"_id": resource_id})
                if not existing:
                    print(resource_data["analysis"])
                    await collection.insert_one(resource_data)
                    print(f"Inserted into existing collection: {best_collection}")
                else:
                    logger.info(f"Resource already exists in {best_collection}, skipping.")
                    print(f"Resource already exists in {best_collection}, skipping.")

            else:
                # Similarity too low — create a new collection named after macro_subject
                print("similarity is too low, creating new collection")
                new_collection_name = resource.analysis.macro_subject.replace(" ", "_").lower()
                collection = db[new_collection_name]
                resp = await collection.insert_one(resource_data)
                print(resp.inserted_id)
                response = await create_search_index(collection_name=new_collection_name, database_name=db.name)
                print(response)
                print(f"Inserted into new collection: {new_collection_name}")

        return UploadResponse(
            success=True,
            message="OERs uploaded successfully",
        )

    except Exception as e:
        print(f"Error during OERs upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/delete-oer", response_model=dict)
async def delete_oer(request: DeleteRequest = Body(...), token: str = Header(..., alias="token"), access_key: str = Header(..., alias="access_key")):
    """
    Delete OERs from the database.
    - **token**: JWT token for user authentication
    - **access_key**: Access key for API authentication
    - **request**: UploadRequest containing the resources ids to delete
    This endpoint allows admins to delete OERs from the database.
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        username, _, _ = await validate_token(user_db, token, SECRET_KEY, ALGORITHM)
        print(f"Authenticated user: {username}")
        # Get user's personal collection
        user_collection = user_db[username]

        # Get user's profile document
        profile: UserProfileDocument = await get_profile(user_collection)
        user_profile = UserProfileDocument(**profile)

        role = user_profile.personal_info.role

        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete OERs"
            )

        # Delete the OERs from the collection
        for resource_id in request.resources_ids:
            # Find the collection that contains the resource
            collection = request.collection_name
            if not collection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Collection name is required"
                )
            result = await db[collection].delete_one({"_id": ObjectId(resource_id)})
            if result.deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Resource with ID {resource_id} not found in collection {collection}"
                )

        return {"success": True, "message": "OERs deleted successfully"}

    except Exception as e:
        print(f"Error during OERs deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/get-oers-collections", response_model=List[str])
async def get_oers_collections(access_key: str = Header(..., alias="access_key")) -> List[str]:
    """
    Retrieve the list of OERs collections in the database.

    - **access_key**: API access key for authentication.
    
    Returns a list of collection names available in the OERs database.
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        # Get the list of collections in the database
        collections: List[str] = await db.list_collection_names()
        
        if not collections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No collections found in the database."
            )

        return collections

    except Exception as e:    
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
    )

@router.post("/get-oers/", response_model=List[ResourceDocumentSimplified], 
    summary="Retrieve OERs from a Collection",
    description="""Get Open Educational Resources (OERs) from a specific MongoDB collection using various filters such as title, description (vector search), and education level.

### Request Body (Filters):
- **collection_name** (str, required): Name of the MongoDB collection to search in.
- **title** (str, optional): Exact or partial title of the resource. If provided, the API will attempt exact and regex matches on the 'analisys.title' field.
- **description** (str, optional): A text string to run a vector-based semantic search. Returns resources semantically similar to the description.
- **education_level** (str, optional): Education level to filter the results (e.g., "primary", "secondary", "higher").

### Header Parameters:
- **access_key** (str, required): API access key for authentication.

### Behavior:
1. If `title` is provided, performs exact and partial (regex) title search.
2. If `description` is provided, performs vector similarity search (requires the vector search backend).
3. If `education_level` is provided, filters resources by this field.
4. If no filters match, returns all documents in the specified collection.

### Responses:
- **200 OK**: List of matching resources, each as a `ResourceDocumentSimplified` model.
- **400 Bad Request**: If `collection_name` is missing.
- **404 Not Found**: If collection does not exist or no matching resources are found.
- **500 Internal Server Error**: If an unexpected error occurs during processing.
""")
async def get_oers_by_collection(filters: Filters = Body(...), access_key: str = Header(..., alias="access_key")) -> List[ResourceDocumentSimplified]:
    """
    Get OERs from a specific collection based on title, description (vector search placeholder), and education level.
    """
    try:
        print("Authenticating access key...")
        authenticate(access_key)
        print("Authentication successful.")

        if not filters.collection_name:
            print("Missing collection name in filters!")
            raise HTTPException(status_code=400, detail="Collection name is required")

        print(f"Using collection: {filters.collection_name}")
        # list database collections
        collections = await db.list_collection_names()
        print("Collections in database: ", collections)

        if filters.collection_name not in collections:
            print(f"Collection {filters.collection_name} not found in database.")
            raise HTTPException(status_code=404, detail=f"Collection {filters.collection_name} not found in database.")

        cn = filters.collection_name
        collection = db[cn]

        # get the number of documents in the collection:
        num_docs = await collection.count_documents({})
        print(f"Number of documents in collection {cn}: {num_docs}")

        # 1. Title Search
        if filters.title and filters.title.strip() != "":
            print(f"Title filter provided: {filters.title}")

            print("Searching for exact title match...")
            exact_match = await collection.find_one(
                {"analisys.title": filters.title},
                {
                    "_id": 1,
                    "uploaded_at": 1,
                    "analisys": 1,
                    "document_type": 1
                }
            )
            print(f"Exact title match result: {exact_match}")

            if exact_match:
                exact_match["_id"] = str(exact_match["_id"])
                print("Returning exact title match result.")
                return [ResourceDocumentSimplified(**exact_match)]

            print("No exact match found. Searching for partial (regex) matches...")
            similar_titles = await collection.find(
                {"analisys.title": {"$regex": filters.title, "$options": "i"}},
                {
                    "_id": 1,
                    "uploaded_at": 1,
                    "analisys": 1,
                    "document_type": 1
                }
            ).to_list(length=None)

            print(f"Similar titles found: {similar_titles}")

            if similar_titles:
                for doc in similar_titles:
                    doc["_id"] = str(doc["_id"])
                print("Returning similar title matches.")
                return [ResourceDocumentSimplified(**doc) for doc in similar_titles]
            else:
                logger.error("No title matches found at all.")
                print("No title matches found at all.")

        # 2. Description Vector Search
        if filters.description and filters.description.strip() != "":
            print(f"Description filter provided: {filters.description}")

            print("Running vector search placeholder...")
            print(f"Target collection: {filters.collection_name}")
            print(f"Target description: {filters.description}")
            collections: List[Tuple[str, str, float]] = pair_queries_with_collection([filters.description], [filters.collection_name])
            tup: Tuple[str, str, float] = collections[0]
            print(f"Vector search collections result: {collections[0]}")

            collection_name = tup[1]
            print(f"Target collection for vector search: {collection_name}")

            res: List[Grounding] = await find_resources_from_queries([filters.description], collection_name, k=5, db_name=DB_NAME, score_threshold=SCORE_THRESHOLD)
            print(f"Vector search resources (Grounding): {res}")

            resource_ids = [doc.resource for doc in res]
            print(f"Resource IDs from vector search: {resource_ids}")

            if not resource_ids:
                print("No resources found via vector search.")
                raise HTTPException(status_code=404, detail="No resources found from vector search.")

            cursor = collection.find(
                {"_id": {"$in": [ObjectId(rid) for rid in resource_ids]}, "document_type": "resource"},
                {
                    "_id": 1,
                    "uploaded_at": 1,
                    "analysis": 1,
                    "document_type": 1
                }
            )
            resource_documents = await cursor.to_list(length=None)
            print(f"Resource documents retrieved from DB: {resource_documents}")

            if not resource_documents:
                print("No resources found via vector search.")
                raise HTTPException(status_code=404, detail="No resources found from vector search.")

            for doc in resource_documents:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

            print("Converting MongoDB docs to Pydantic models...")
            resource_list = [ResourceDocumentSimplified(**doc) for doc in resource_documents]
            print(f"Converted resource list: {resource_list}")

            if resource_list:
                if filters.education_level and filters.education_level.value != "":
                    print(f"Filtering vector results by education level: {filters.education_level.value}")
                    final_resources = [
                        doc for doc in resource_list
                        if doc.analysis and doc.analysis.education_level == filters.education_level.value
                    ]
                    print(f"Resources after education level filter: {final_resources}")
                    resource_list = final_resources

                print("Returning vector search results.")
                return resource_list

        # 3. Only Education Level Filter (if no description or no vector results)
        if filters.education_level and filters.education_level.value != "":
            print(f"Education level filter provided: {filters.education_level.value}")
            level_filtered_docs = await collection.find({
                "analysis.education_level": filters.education_level.value
                },
                {
                    "_id": 1,
                    "uploaded_at": 1,
                    "analysis": 1,
                    "document_type": 1
                }
            ).to_list(length=None)

            print(f"Documents matching education level: {level_filtered_docs}")

            if level_filtered_docs:
                for doc in level_filtered_docs:
                    doc["_id"] = str(doc["_id"])
                print("Returning education level filtered documents.")
                return [ResourceDocumentSimplified(**doc) for doc in level_filtered_docs]
            else:
                print("No documents found matching the education level filter.")
                raise HTTPException(status_code=404, detail="No documents found matching the education level filter.")

        # 4. If no specific filters matched, return everything
        print("No filters matched. Returning all documents in the collection.")
        all_docs = await collection.find({},{
                    "_id": 1,
                    "uploaded_at": 1,
                    "analysis": 1,
                    "document_type": 1
                }).to_list(length=None)

        for doc in all_docs:
            doc["_id"] = str(doc["_id"])

        print(f"Returning all documents: {all_docs}")
        return [ResourceDocumentSimplified(**doc) for doc in all_docs]

    except Exception as e:
        print(f"Error during OER retrieval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-complete-oer/", response_model=Resource)
async def get_oer_by_id(request: GetResourceRequest = Body(...), access_key: str = Header(..., alias="access_key")):
    """
    Get a specific OER by its ID.
    - **resource_id**: The ID of the OER to retrieve
    - **access_key**: Access key for API authentication
    """
    try:
        # Authenticate access key
        authenticate(access_key)

        collection = db[request.collection_name]
        resource = await collection.find_one({"_id": ObjectId(request.resource_id)})
        if resource:
            resource["_id"] = str(resource["_id"])
            return Resource(**resource)

        raise HTTPException(status_code=404, detail="Resource not found")

    except Exception as e:
        print(f"Error during OER retrieval by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

