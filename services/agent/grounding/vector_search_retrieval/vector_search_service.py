from collections import defaultdict
import os
from typing import List, Tuple
import numpy as np
from pymongo import MongoClient
from sklearn.metrics.pairwise import cosine_similarity
from motor.motor_asyncio import AsyncIOMotorClient


from langchain_huggingface import HuggingFaceEmbeddings

from services.agent.grounding.vector_search_retrieval.vector_search_utils import VectorSearchResults
from services.agent.orchestrator.chat.chat_utils import Resource
from services.agent.orchestrator.orchestrator.agent_utils import Grounding

# MongoDB connection - using async client
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # MongoDB URI
SCORE_THRESHOLD = 0.5

def pair_queries_with_collection(
    queries: List[str], 
    collections: List[str], 
    embeddings: HuggingFaceEmbeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
) -> List[Tuple[str, str, float]]:
    """
    For each query, find the closest matching collection based on cosine similarity.
    
    Returns:
        List of tuples in the form: (query, best_matching_collection_name, similarity_score)
    """
    print("Starting pair_queries_with_collection...")
    print(f"Queries received: {queries}")
    print(f"Collections received: {collections}")

    # Compute embeddings
    print("Computing embeddings for queries...")
    query_embeddings = embeddings.embed_documents(queries)
    print(f"Query embeddings shape: {np.array(query_embeddings).shape}")

    print("Computing embeddings for collections...")
    collection_embeddings = embeddings.embed_documents(collections)
    print(f"Collection embeddings shape: {np.array(collection_embeddings).shape}")

    results: List[Tuple[str, str, float]] = []

    # Pair each query to the closest collection
    for i, query_embedding in enumerate(query_embeddings):
        print(f"\nProcessing query {i}: '{queries[i]}'")

        # Compute cosine similarity between this query embedding and all collection embeddings
        similarities = cosine_similarity([query_embedding], collection_embeddings)
        print(f"Similarities array: {similarities}")

        best_match_idx = np.argmax(similarities)
        print(f"Best matching index: {best_match_idx}")

        best_collection = collections[best_match_idx]
        best_similarity = similarities[0][best_match_idx]
        print(f"Best matching collection: '{best_collection}' with similarity score: {best_similarity}")

        # Append the result including similarity score for debugging purposes
        results.append((queries[i], best_collection, float(best_similarity)))

    print(f"\nFinal pairing results: {results}")
    return results


async def query_OERs(queries: List[str])->List[VectorSearchResults]:
    """Query MongoDB Atlas for relevant chunks."""
    # Get the available macro subjects collections
    client = MongoClient(MONGO_URI)
    db = client["OERs"]
    collections: List[str] = db.list_collection_names()

    if not collections:
        raise Exception("No collections found in the database.")
    
    # Use embeddings to find the most relevant collection
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    best_collection_pairs = pair_queries_with_collection(queries, collections, embeddings)

    # Group the queries by collection
    queries_by_collection = {}
    for query, collection_name, similarity in best_collection_pairs:
        if collection_name not in queries_by_collection:
            queries_by_collection[collection_name] = []
        queries_by_collection[collection_name].append(query)

    best_resources: List[VectorSearchResults] = []
    for collection_name, collection_queries in queries_by_collection.items():
        # Find, for each collection, the best resources for the queries
        groundings = await find_resources_from_queries(collection_queries, collection_name, score_threshold=0.7, db_name="OERs", k=3)
        # Perform grounding on the best resources
        result = await query_documents_with_filter(groundings, collection_name)
        # Extend the grounding responses
        best_resources.extend(result)

    return best_resources
    
async def query_documents_with_filter(
    grounding: List[Grounding],
    collection_name: str,
    score_threshold: float = SCORE_THRESHOLD,
    k: int = 3,
) -> List[VectorSearchResults]:
    """
    Query documents with optional filtering on resource IDs.
    If resource_ids is None or empty, no filtering on resource IDs is applied.
    """
    from services.agent.orchestrator.chat.chat_service import get_complete_resources_by_ids
    # MongoDB connection - using async client
    client = AsyncIOMotorClient(MONGO_URI)
    db = client["user_data"]
    user_collection = db[collection_name]

    final_results: List[VectorSearchResults] = []

    for doc in grounding:
        doc_id = doc.resource
        #retrive the complete doc
        resources: List[Resource] = await get_complete_resources_by_ids(user_collection, [doc_id])
        resource: Resource = resources[0]

        queries = doc.grounding_queries
        results = vector_search_with_filter(
            resource=resource,
            queries=queries,
            score_threshold=score_threshold,
            k=k,
        )

        final_results.extend(results)

    return final_results

def vector_search_with_filter(
    resource: Resource,
    queries: List[str],
    score_threshold: float = 0.0,
    k: int = 3,
) -> List[VectorSearchResults]:
    """
    Performs vector search for a given set of queries and returns the top k results.
    Returns the query string, the resource id, resource title, and top k matches with similarity, text, and page.
    """
    # Get embeddings for queries
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    queries_embeddings = embeddings.embed_documents(queries)  # shape: [num_queries, 768]

    results: List[VectorSearchResults] = []

    # Extract document embeddings and associated data
    doc_texts = []
    doc_embeddings = []
    doc_pages = []

    for item in resource.content:
        text = item.get("text", "")
        embedding = item.get("embedding", [])
        metadata = item.get("metadata", {})

        page = 0
        if isinstance(metadata, dict):
            page = metadata.get("page", 0)

        doc_texts.append(text)
        doc_embeddings.append(embedding)
        doc_pages.append(page)

    doc_embeddings_np = np.array(doc_embeddings)  # shape: [num_docs, 768]

    for query_text, query_embedding in zip(queries, queries_embeddings):
        query_embedding_np = np.array(query_embedding).reshape(1, -1)  # shape: [1, 768]

        # Compute cosine similarity
        similarities = cosine_similarity(query_embedding_np, doc_embeddings_np)[0]  # shape: [num_docs]

        # Collect similarity, text, and page
        scored_results = [
            (score, text, page) for score, text, page in zip(similarities, doc_texts, doc_pages) if score >= score_threshold
        ]

        # Sort by similarity descending
        top_results = sorted(scored_results, key=lambda x: x[0], reverse=True)[:k]

        result = VectorSearchResults(
            query=query_text,
            resource_id=resource.id,
            resource_title=resource.analysis.title,
            pairings=top_results
        )
        results.append(result)

# -------------- Global De-duplication (safe version) --------------

    global_text_map = {}  # signature -> (best_score, res_idx, pair_idx)

    # First pass: determine the best (highest score) occurrence for each unique text signature
    for res_idx, result in enumerate(results):
        for pair_idx, (score, text, page) in enumerate(result.pairings):
            signature = text[:10] + text[-10:]
            if signature not in global_text_map:
                global_text_map[signature] = (score, res_idx, pair_idx)
            else:
                existing_score, existing_res_idx, existing_pair_idx = global_text_map[signature]
                if score > existing_score:
                    global_text_map[signature] = (score, res_idx, pair_idx)

    # Second pass: keep only the "winning" occurrence for each text
    for res_idx, result in enumerate(results):
        new_pairings = []
        for pair_idx, (score, text, page) in enumerate(result.pairings):
            signature = text[:10] + text[-10:]
            best_score, best_res_idx, best_pair_idx = global_text_map[signature]
            if res_idx == best_res_idx and pair_idx == best_pair_idx:
                new_pairings.append((score, text, page))  # keep only the best occurrence
        result.pairings = new_pairings  # safely replace the list

    # Third pass: if some query has no pairings left, remove it completely
    new_results = []
    for result in results:
        if result.pairings:
            new_results.append(result)
    results = new_results

    print("\n" + "-"*50 + "\n" + "\n".join(result.to_str() for result in results))

    return results


async def find_resources_from_queries(
    queries: List[str],
    collection_name: str,
    score_threshold: float = 0.5,
    db_name: str = "user_data",
    k: int = 2,
) -> List[Grounding]:
    """
    For each query, find top-k resources above the threshold.
    Then, group the results by resource ID, collecting the list of queries that matched that resource.
    Returns: List of (resource_id, [list of matching queries])
    """
    client = MongoClient(MONGO_URI)
    db = client[db_name]
    index_name = "embedding_vector_index"
    collection = db[collection_name]

    print(db_name, collection_name)

    resource_to_queries = defaultdict(list)  # resource_id -> list of queries that matched it

    for query in queries:
        try:
            print(f"Processing query: {query}")
            cursor = collection.aggregate([
                {
                    '$search': {
                        'index': index_name,
                        'text': {
                            'query': query,
                            'path': {
                                'wildcard': "*",
                            },
                        }
                    }
                },
                {
                    '$project': {
                        '_id': 1,
                        'score': {'$meta': 'searchScore'}
                    }
                }
            ])

            docs = list(cursor)  # Consume cursor
            if not docs:
                print(f"No documents found for query: {query}")
                continue

            # Get max similarity
            max_similarity = 1
            if len(docs) >1:
                max_similarity = max(doc['score'] for doc in docs)

            # Collect resources above threshold
            query_results = []
            for doc in docs:
                print(f"Document ID: {doc['_id']}, Similarity: {doc['score']}")
                normalized_score = doc['score'] / max_similarity if max_similarity > 0 else 0
                if normalized_score >= score_threshold:
                    query_results.append((doc['_id'], doc['score']))

            if len(query_results) == 0 or not query_results:
                print(f"No results above threshold for query: {query}")
                continue

            # Top-k by score
            query_results = sorted(query_results, key=lambda x: x[1], reverse=True)[:k]

            for doc_id, score in query_results:
                resource_to_queries[str(doc_id)].append(query)

        except Exception as e:
            print(f"Error during aggregation for query '{query}': {e}")
            continue

    # Convert to list of Grounding objects
    groundings = [
        Grounding(resource=resource_id, grounding_queries=query_list)
        for resource_id, query_list in resource_to_queries.items()
    ]

    #print("\nFinal Grounding Objects:")
    #for grounding in groundings:
    #    print(grounding.model_dump())

    return groundings
