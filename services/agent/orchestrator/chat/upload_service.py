import asyncio
import os
import re
import sys
import json
import aiofiles
from fastapi import File, Form, UploadFile
from fastapi.encoders import jsonable_encoder
from typing import Any, Dict, List, Tuple, Optional
from motor.motor_asyncio import AsyncIOMotorCollection

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings

from services.agent.grounding.analyse_material.analyse_material_service import analysis, get_text_from_source
from services.agent.grounding.analyse_material.analyse_material_utils import AnalyseMaterialRequest, Analysis
from services.agent.orchestrator.chat.chat_utils import Resource

import logging
logger = logging.getLogger(__name__)

MAX_DOC_SIZE = 16 * 1024 * 1024  # 16MB limit in bytes
SAFETY_MARGIN = 10000  # some extra bytes to prevent close overflows
TEMP_FOLDER = "temp_files" # Folder to store temporary files
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", "pptx", ".png", ".jpg", ".jpeg"} # Allowed file extensions


def clean_text(text):
    """Replace newlines with spaces unless they indicate a paragraph break."""
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # Replace single newlines with a space
    text = re.sub(r"\n{2,}", "\n\n", text)  # Preserve paragraph breaks
    return text.strip()

def load_pdf(file_path):
    """Load a PDF and clean text per page."""
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    if len(pages) == 0:
        error = Exception(f"Document is empty")
        error.status_code = 400
        raise error
    
    for page in pages:
        page.page_content = clean_text(page.page_content)
    print(f"read {len(pages)} pages from {file_path}")
    return pages

def split_text(pages, min_chars=500) -> List[Tuple[str, Dict[str, int]]]:
    """
    Splits text from multiple pages into non-overlapping chunks. Each chunk:
      - Is at least min_chars characters long (except possibly the last chunk),
      - Starts at the beginning of a phrase,
      - Ends at the end of a phrase (i.e. ends with punctuation),
      - And its metadata 'page' is the number of the page where the chunk begins.
    
    Args:
        pages (List[Any]): List of page-like objects, each having a `page_content` (str) attribute.
        min_chars (int, optional): Minimum number of characters per chunk. Defaults to 500.
    
    Returns:
        List[Tuple[str, Dict[str, int]]]: List of (chunk_text, {"page": page_number}) tuples.
    """
    chunks: List[Tuple[str, Dict[str, int]]] = []
    current_chunk: str = ""
    current_page_start: int | None = None
    page_number: int = 1

    for page in pages:
        sentences = re.split(r'(?<=\.)\s|\n\n', page.page_content)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if not current_chunk:
                current_chunk = sentence
                current_page_start = page_number
            else:
                current_chunk += " " + sentence

            if len(current_chunk) >= min_chars and re.search(r"[.!?](”|')?$", current_chunk):
                chunks.append((current_chunk, {"page": current_page_start}))
                current_chunk = ""
                current_page_start = None

        page_number += 1

    if current_chunk:
        chunks.append((current_chunk, {"page": current_page_start}))

    return chunks

def compute_cosine_similarity(e1: List[float], e2: List[float]) -> float:
    """
    Computes the cosine similarity between two embedding vectors.

    Args:
        e1 (List[float]): First embedding vector.
        e2 (List[float]): Second embedding vector.

    Returns:
        float: Cosine similarity between the two vectors.
    """
    e1_array = np.array(e1).reshape(1, -1)
    e2_array = np.array(e2).reshape(1, -1)
    sim: float = cosine_similarity(e1_array, e2_array)[0][0]
    return sim

def compute_similarities(embeddings: List[List[float]]) -> Tuple[List[float], float]:
    """
    Compute cosine similarities between each embedding and its right neighbor.

    Args:
        embeddings (List[List[float]]): List of embedding vectors.

    Returns:
        Tuple[List[float], float]: 
            - List of cosine similarities between each adjacent embedding pair.
            - Average of these similarities.
    """
    similarities: List[float] = []
    e1 = np.array(embeddings[0]).reshape(1, -1)

    for i in range(len(embeddings) - 1):
        e2 = np.array(embeddings[i + 1]).reshape(1, -1)
        sim: float = cosine_similarity(e1, e2)[0][0]
        similarities.append(sim)
        e1 = e2

    avg_inter_similarity: float = float(np.mean(similarities))
    return similarities, avg_inter_similarity

def iterative_merging(chunks: List[Tuple[str, Dict[str, int]]], model_name: str = "sentence-transformers/all-mpnet-base-v2") -> List[Tuple[str, Dict[str, int]]]:
    """
    Perform iterative merging of text chunks based on semantic similarity until dissimilarity stops improving.

    Args:
        chunks (List[Tuple[str, Dict[str, int]]]): 
            List of tuples containing text chunks and their metadata (must include 'page' key).
        model_name (str, optional): 
            Name of the SentenceTransformer model to use for embeddings.

    Returns:
        List[Tuple[str, Dict[str, int]]]: 
            Merged chunks after iterative similarity-based grouping.
    """
    # Extract text for embedding
    texts: List[str] = [chunk[0] for chunk in chunks]
    model = SentenceTransformer(model_name)
    embeddings: np.ndarray = model.encode(texts, convert_to_numpy=True)
    similarities, avg_inter_similarity = compute_similarities(embeddings)
    print("Initial average inter chunk similarity:", avg_inter_similarity)

    groups: List[Tuple[
        List[int],                     # Indices of merged chunks
        Tuple[str, Dict[str, int]],    # Merged chunk (text, metadata)
        np.ndarray,                    # Merged embedding
        float                          # Avg intra similarity
    ]] = []

    threshold: float = 0.95
    average_silhouette: float = 0.0

    while len(groups) != 1 and threshold > 0.6:
        last_index: int = 0
        valid_groups: int = 0

        while last_index <= len(similarities):  
            i: int = last_index
            current_group: List[int] = [i]
            
            # Group chunks based on similarity threshold
            while i < len(similarities) and similarities[i] > threshold:
                i += 1
                current_group.append(i)

            complete_text: str = "".join(chunks[elem][0] for elem in current_group)
            
            if len(current_group) > 1:
                merged_emb: np.ndarray = model.encode(complete_text, convert_to_numpy=True)
            else:
                merged_emb = embeddings[current_group[0]]

            new_chunk: Tuple[str, Dict[str, int]] = (
                complete_text,
                {"page": chunks[current_group[0]][1]['page']}
            )

            if len(current_group) > 1:
                intra_similarities: List[float] = [
                    compute_cosine_similarity(embeddings[j], merged_emb) for j in current_group
                ]
                avg_intra_similarity: float = float(np.mean(intra_similarities))
                valid_groups += 1
            else:
                avg_intra_similarity = 0.0

            print(f"Average intra-similarity: {avg_intra_similarity}, Group members: {current_group}")
            print(f"Last similarity: {similarities[i]}" if i < len(similarities) else "none")

            groups.append((current_group, new_chunk, merged_emb, avg_intra_similarity))

            last_index = i + 1

        new_inter_similarities: List[float] = []
        for i in range(len(groups) - 1):
            sim: float = compute_cosine_similarity(groups[i][2], groups[i + 1][2])
            new_inter_similarities.append(sim)

        new_avg_inter_similarity: float = float(np.mean(new_inter_similarities))
        print(f"New average inter-similarity: {new_avg_inter_similarity}, within {len(new_inter_similarities)} groups")

        if valid_groups == 0:
            new_avg_intra_similarity: float = 0.0
        else:
            new_avg_intra_similarity = sum(group[3] for group in groups) / valid_groups

        print(f"New average intra-similarity: {new_avg_intra_similarity} for {valid_groups} groups")

        if new_avg_intra_similarity != 0:
            new_average_silhouette: float = (
                (new_avg_intra_similarity - new_avg_inter_similarity) / 
                max(new_avg_intra_similarity, new_avg_inter_similarity)
            )
            if new_average_silhouette <= average_silhouette:
                print("Average silhouette did not improve.")
                break
            else:
                logger.info(f"Average silhouette improved to {new_average_silhouette}")
                print(f"Average silhouette improved to {new_average_silhouette}")

        print("-" * 50)
        similarities = new_inter_similarities
        embeddings = [group[2] for group in groups]
        chunks = [group[1] for group in groups]
        groups = []
        threshold -= 0.1

    return chunks

def generate_final_embeddings(
    chunks: List[Tuple[str, Dict[str, int]]]
) -> List[List[float]]:
    """
    Generate embeddings for text chunks using HuggingFaceEmbeddings.

    Args:
        chunks (List[Tuple[str, Dict[str, int]]]): 
            List of text chunks and their metadata.

    Returns:
        List[List[float]]: 
            List of embedding vectors for each chunk.
    """
    model_name: str = "sentence-transformers/all-mpnet-base-v2"
    hf_embeddings = HuggingFaceEmbeddings(model_name=model_name)
    final_embeddings: List[List[float]] = [
        hf_embeddings.embed_query(chunk[0]) for chunk in chunks
    ]
    return final_embeddings

def semantic_chunking(file_path: str) -> List[Dict[str, Any]]:
    """
    Perform semantic chunking and embedding generation for a PDF document.

    Args:
        file_path (str): Path to the resource.

    Returns:
        List[Dict[str, Any]]: List of documents containing 'text', 'embedding', and 'metadata' ready for MongoDB storage.
    """
    # Load the source
    try:
        pages = get_text_from_source(file_path)  # pages: List[Page] or similar, depending on your PDF loader
    except Exception as e:
        raise

    chunks: List[Tuple[str, Dict[str, int]]] = split_text(pages)
    print(f"Loaded {len(chunks)} chunks from {file_path}.")

    if len(chunks) == 0:
        error = Exception("Document is empty")
        error.status_code = 400
        raise error

    if len(chunks) > 1:
        final_chunks: List[Tuple[str, Dict[str, int]]] = iterative_merging(chunks)
        print(f"Merged into {len(final_chunks)} chunks.")
    else:
        final_chunks = chunks

    if len(final_chunks) < 2:
        error = Exception("Document is too short.")
        error.status_code = 400
        raise error

    final_chunks_embeddings: List[List[float]] = generate_final_embeddings(final_chunks)
    print(f"Generated embeddings for {len(final_chunks)} chunks.")

    # Prepare documents for MongoDB
    documents: List[Dict[str, Any]] = []
    for (text, metadata), embedding in zip(final_chunks, final_chunks_embeddings):
        doc: Dict[str, Any] = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata
        }
        documents.append(doc)

    return documents



def calculate_size(obj: dict) -> int:
    """Calculate size of object in bytes."""
    return len(json.dumps(obj).encode('utf-8'))

def split_into_mongo_documents(
    analysis: Analysis,
    chunks: List[Dict[str, Any]],
    max_document_size: int = 16 * 1024 * 1024  # 16 MB in bytes
) -> List[Resource]:
    """
    Splits analysis and chunks into multiple Resource documents,
    each not exceeding MongoDB's 16MB document limit.

    :param analysis: Analysis result (as Analysis Pydantic model).
    :param chunks: List of chunk dicts (text, embedding, metadata).
    :param max_document_size: Maximum size per document in bytes (default: 16MB).
    :return: List of Resource objects ready for insertion.
    """

    documents: List[Resource] = []
    current_chunks: List[Dict[str, Any]] = []

    # Calculate the size of the analysis part
    analysis_size = sys.getsizeof(analysis)
    print(f"Analysis size: {analysis_size} bytes")

    # Safety check: if analysis itself is bigger than 16MB
    if analysis_size >= max_document_size:
        raise ValueError("Analysis part alone exceeds the 16MB MongoDB document limit.")

    for chunk in chunks:
        chunk_size = sys.getsizeof(chunk)

        # Estimate total size if this chunk is added
        current_total_size = (
            analysis_size + sum(sys.getsizeof(c) for c in current_chunks) + chunk_size
        )

        if current_total_size >= max_document_size and current_chunks:
            # Create a Resource document with the current chunks
            resource = Resource(
                analysis=analysis,
                content=current_chunks.copy()
            )
            documents.append(resource)
            # Reset current chunks
            current_chunks = []

        current_chunks.append(chunk)

    # Add any remaining chunks in the last document
    if current_chunks and len(current_chunks) > 0:
        resource = Resource(
            analysis=analysis,
            content=current_chunks.copy()
        )
        documents.append(resource)

    return documents

# Simple URL validation regex (can be expanded)
URL_REGEX = re.compile(
    r'^https://'   # https:
    r'(\S+(:\S*)?@)?'  # optional username:password@
    r'([A-Za-z0-9.-]+)'  # domain
    r'(:\d+)?'  # optional port
    r'(\/\S*)?$'  # path
)

async def check_file(file: Optional[UploadFile] = File(None), url: Optional[str] = Form(None)) -> str:
    # 1. Error: Neither file nor URL provided
    if file is None and url is None:
        return "Error: No file or URL provided."

    # 2. Handle file upload
    if file is not None:
        # Check extension
        _, ext = os.path.splitext(file.filename)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            return f"Error: File extension '{ext}' is not allowed."

        # Sanitize filename to avoid path traversal etc.
        safe_filename = os.path.basename(file.filename)
        save_path = os.path.join(TEMP_FOLDER, safe_filename)

        try:
            # Save file asynchronously
            async with aiofiles.open(save_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
        except Exception as e:
            return f"Error: Failed to save file. {str(e)}"

        return save_path

    # 3. Handle URL
    if url is not None:
        # Basic URL validation
        if not URL_REGEX.match(url):
            return "Error: Invalid or potentially unsafe URL."

        # Further validation can be added (like domain whitelisting)
        return url

    # This should not happen
    return "Error: Unknown error occurred."

async def delete_temp_file(file_path: str):
    if os.path.exists(file_path):
        # Since os.remove is sync, run it in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, os.remove, file_path)
        return f"Deleted file {file_path}"
    else:
        return f"File {file_path} does not exist"

async def upload(
    collection: AsyncIOMotorCollection,
    model: str = "Gemini",
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    """
    Upload a file (by path) and perform semantic chunking.
    """
    try: 
        # Upload the material to the server and check if it's safe
        if file is not None and file.filename != "":
            logger.info(f"Received file: {file.filename}")
            print(f"Received file: {file.filename}")
        elif url is not None and url != "":
            logger.info(f"Received URL: {url}")
            print(f"Received URL: {url}")
        else:
            raise ValueError("No file or URL provided for upload.")
        file_path: str = await check_file(file=file if file else None, url=url if url else None)
        # Analize the material
        url = file_path
        analyze_material_request = AnalyseMaterialRequest(text=url, model=model)
        analysed_material = analysis(analyze_material_request) 
        print(f"Analyzed material: {analysed_material}")
        analysis_dict = jsonable_encoder(analysed_material)

        # Perform semantic chunking
        chunks = semantic_chunking(file_path)

        # Split into MongoDB documents
        documents: List[Resource] = split_into_mongo_documents(analysis_dict, chunks)

        documents_dicts = []

        for resource in documents:
            # Convert Resource to dict and remove any None values
            chat_doc_dict = jsonable_encoder(resource, exclude_none=True)
            documents_dicts.append(chat_doc_dict)
        
        # Insert documents into collection
        result = await collection.insert_many([resource for resource in documents_dicts])

        # Delete the temp_file if it was uploaded
        if file is not None and file.filename != "":
            await delete_temp_file(file_path)
    
        if result.inserted_ids:
            print(f"Inserted {len(result.inserted_ids)} documents into MongoDB.")
            return str(result.inserted_ids[0])
        else:
            raise Exception("No documents were inserted into MongoDB.")

    except Exception as e:
        raise

