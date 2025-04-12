# FastAPI Vector Search API Documentation

## Overview

This API provides functionality to perform vector search queries against a MongoDB collection. Users can send a query, and the API will return results from the collection, including the page number and content extracted from matching documents. The search is performed based on semantic matching using vector representations.

## Endpoints

### POST /vector_search/query

#### Description:
This endpoint allows users to perform a query search on a collection in MongoDB. The API uses the query string to retrieve matching documents and returns the page number and content of the matching documents.

#### Request Body:

```json
{
  "query": "string",               // Required. The query string to search for.
  "uri": "string",                 // Optional. The MongoDB connection URI.
  "db_name": "string",             // Optional. The name of the MongoDB database.
  "collection_name": "string"     // Optional. The name of the MongoDB collection.
}
```
### Request Body Fields

- **query**: Required. The query to search for within the collection.
- **uri**: Optional. The MongoDB connection URI. If not provided, environment variables will be used.
- **db_name**: Optional. The name of the MongoDB database. If not provided, a default value of `edu_db` will be used.
- **collection_name**: Optional. The name of the MongoDB collection. If not provided, a default value of `materials` will be used.

### Responses

#### 200 OK:
- **Successful Call**: Returns a JSON response with a status code of 200 and a message indicating the query was successful, along with the search results containing page numbers and content.

#### Error Handling
- **Query Too Short**: Returns a 400 Bad Request with the error message: "Query is too short, please contextualize more."
- **No Results Found**: Returns a 400 Bad Request with the error message: "No results found. Please write a coherent query."
- **Not Found**: Returns a 404 Not Found error.
- **Validation Error**: Returns a 422 Unprocessable Entity error if the query fails validation (e.g., too short).
- **Internal Server Error**: Returns a 500 Internal Server Error if there’s an unexpected issue during query processing.
