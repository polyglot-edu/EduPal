from common.mongodb_connection import get_mongo_collection

from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_huggingface import HuggingFaceEmbeddings

def query_documents(query, uri, db_name, collection_name, k=1):
    """Query MongoDB Atlas for relevant chunks."""
    print(f"Querying for: {query}")
    # Connect to MongoDB
    collection = get_mongo_collection(db_name, collection_name, uri)
   
    # Initialize vector store
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    vector_store = MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
        index_name="primary"
    )
    
    # Perform similarity search
    try:
        results = vector_store.similarity_search(query, k=k, include_scores=True)
    except Exception as e:
        print(f"Error during search: {e}")

    print(f"Found {len(results)} results for query: {query}")
    
    if not results:
        print("No results found. Consider checking if embeddings were stored correctly and index exists.")
    
    for result in results:
        page_number = result.metadata.get('metadata', {}).get("page", "Unknown")
        print(f"Page: {page_number}")
        print(result.page_content[:50],"...\n")
        print("Score:", result.metadata.get("score", 0))
        print("-" * 50)
        if result.metadata.get("score", 0) < 0.7:
            print("Score is too low")
            results.remove(result)
    if len(results) == 0:
        error = Exception("No results found. Please write a coherent query.")
        error.status_code = 400
        raise error

    return results