# `get_mongo_collection` Function

Returns a collection from a specific database with detailed error handling.

This function connects to a MongoDB instance, verifies the existence of a specified 
database and collection, and returns the requested collection. It includes detailed 
error handling for connection issues, missing databases, and missing collections.

## Parameters

- `db_name` (str): The name of the database to connect to. The function will verify if the database exists on the MongoDB server.
- `collection_name` (str): The name of the collection to retrieve from the specified database. The function will verify if the collection exists within the specified database.
- `uri` (str): The connection URI to the MongoDB instance. The URI should be in the form: `mongodb://username:password@host:port/`.

## Returns

- `pymongo.collection.Collection`: The specified collection from the MongoDB database.

## Raises

- `ConnectionError`: If there is an issue connecting to the MongoDB instance. This could be due to an incorrect URI or a server failure.
- `ValueError`: If the specified database or collection does not exist on the MongoDB server.
- `RuntimeError`: For any errors that occur during MongoDB operations, such as query failures or other operational issues.

## Example Usage

```python
uri = "mongodb://localhost:27017/"
db_name = "test_database"
collection_name = "test_collection"

try:
    collection = get_mongo_collection(db_name, collection_name, uri)
    print("Collection retrieved successfully")
except (ConnectionError, ValueError, RuntimeError) as e:
    print(f"Error: {e}")
