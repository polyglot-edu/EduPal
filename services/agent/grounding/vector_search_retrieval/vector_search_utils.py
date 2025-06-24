from typing import List, Tuple
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    uri: str = None
    db_name: str = None
    collection_name: str = None

class QueryResult(BaseModel):
    page: int  # Page number extracted from metadata
    content: str  # Extracted page content

class QueryResponse(BaseModel):
    result: str
    search_results: List[QueryResult]  # List of results with metadata and content

class VectorSearchResults(BaseModel):
    query: str
    resource_id: str
    resource_title: str
    pairings: List[Tuple[float, str, int]] # similarity, text, page

    def to_str(self):
        return f"Query: {self.query}\nResource ID: {self.resource_id}\nResource Title: {self.resource_title}\nPairings:\n {self.pairings_to_str()}\n"

    def pairings_to_str(self):
        return "\n".join([f"\nSimilarity: {similarity:.3f}\n      Text: \"{text}\"\n Page: {page}" for similarity, text, page in self.pairings])

