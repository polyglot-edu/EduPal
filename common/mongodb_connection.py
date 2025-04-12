from pymongo import MongoClient, errors

def get_mongo_collection(db_name, collection_name, uri):
    """Returns a collection from a specific database with detailed error handling. 
    This function connects to a MongoDB instance, verifies the existence of a specified database
    and collection, and returns the requested collection. It includes detailed error handling for
    connection issues, missing databases, and missing collections."""
    try:
        # Attempt to connect to MongoDB
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)  # 5s timeout
        client.admin.command('ping')  # Test connection
    except errors.ServerSelectionTimeoutError:
        raise ConnectionError("Failed to connect to MongoDB. Check the URI and server status.")
    except errors.PyMongoError as e:
        raise RuntimeError(f"MongoDB connection error: {e}")
    
    try:
        # Access the specified database
        if db_name not in client.list_database_names():
            raise ValueError(f"Database '{db_name}' does not exist.")
        db = client[db_name]
        
        # Access the specified collection
        if collection_name not in db.list_collection_names():
            raise ValueError(f"Collection '{collection_name}' does not exist in database '{db_name}'.")
        
        return db[collection_name]
    except errors.PyMongoError as e:
        raise RuntimeError(f"MongoDB operation error: {e}")
