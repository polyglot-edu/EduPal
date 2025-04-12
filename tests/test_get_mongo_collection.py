import pytest 
from unittest.mock import patch
from pymongo import errors 
from common.mongodb_connection import get_mongo_collection

@pytest.fixture
def mock_mongo_client():
    """
    Pytest fixture to mock MongoClient. This replaces the actual MongoDB client with a mock version,
    allowing us to simulate different scenarios without connecting to a real database.
    """
    with patch("common.mongodb_connection.MongoClient") as mock_client:
        yield mock_client  # Provides the mocked MongoClient instance to tests

def test_successful_connection_and_collection(mock_mongo_client):
    """
    Test case for successfully retrieving a database and collection.
    Ensures that get_mongo_collection returns a valid collection object when the database and collection exist.
    """
    # Mocking MongoDB client instance
    mock_client_instance = mock_mongo_client.return_value
    
    # Simulate the existence of the target database
    mock_client_instance.list_database_names.return_value = ["test_db"]
    
    # Simulate getting the database object
    mock_db = mock_client_instance.__getitem__.return_value  
    
    # Simulate the existence of the target collection
    mock_db.list_collection_names.return_value = ["test_collection"]

    # Call the function under test
    collection = get_mongo_collection("test_db", "test_collection", "mongodb://localhost:27017")
    
    # Check that the function returns a valid collection object
    assert collection is not None

def test_connection_failure(mock_mongo_client):
    """
    Test case for MongoDB connection failure.
    Simulates a scenario where the database connection fails due to server unavailability.
    """
    # Simulate a server connection timeout error
    mock_mongo_client.side_effect = errors.ServerSelectionTimeoutError
    
    # Expect the function to raise a ConnectionError with a specific message
    with pytest.raises(ConnectionError, match="Failed to connect to MongoDB. Check the URI and server status."):
        get_mongo_collection("test_db", "test_collection", "mongodb://invalid-uri")

def test_general_connection_error(mock_mongo_client):
    """
    Test case for handling general PyMongo connection errors.
    Ensures that unexpected connection issues raise a RuntimeError.
    """
    # Simulate a general connection error
    mock_mongo_client.side_effect = errors.PyMongoError("Some connection issue")
    
    # Expect a RuntimeError with the corresponding message
    with pytest.raises(RuntimeError, match="MongoDB connection error: Some connection issue"):
        get_mongo_collection("test_db", "test_collection", "mongodb://localhost:27017")

def test_database_does_not_exist(mock_mongo_client):
    """
    Test case for when the specified database does not exist.
    Ensures that a ValueError is raised if the target database is missing.
    """
    # Mocking MongoDB client instance
    mock_client_instance = mock_mongo_client.return_value
    
    # Simulate a scenario where the requested database is not present
    mock_client_instance.list_database_names.return_value = ["other_db"]

    # Expect a ValueError when trying to access a non-existent database
    with pytest.raises(ValueError, match="Database 'test_db' does not exist."):
        get_mongo_collection("test_db", "test_collection", "mongodb://localhost:27017")

def test_collection_does_not_exist(mock_mongo_client):
    """
    Test case for when the specified collection does not exist in the database.
    Ensures that a ValueError is raised if the target collection is missing.
    """
    # Mocking MongoDB client instance
    mock_client_instance = mock_mongo_client.return_value
    
    # Simulate the existence of the requested database
    mock_client_instance.list_database_names.return_value = ["test_db"]
    
    # Simulate getting the database object
    mock_db = mock_client_instance.__getitem__.return_value
    
    # Simulate a scenario where the requested collection does not exist
    mock_db.list_collection_names.return_value = ["other_collection"]

    # Expect a ValueError when trying to access a non-existent collection
    with pytest.raises(ValueError, match="Collection 'test_collection' does not exist in database 'test_db'."):
        get_mongo_collection("test_db", "test_collection", "mongodb://localhost:27017")

def test_mongo_operation_error(mock_mongo_client):
    """
    Test case for MongoDB operation errors such as permission issues or query failures.
    Ensures that an OperationFailure raises a RuntimeError.
    """
    # Mocking MongoDB client instance
    mock_client_instance = mock_mongo_client.return_value
    
    # Simulate an operational failure when listing database names
    mock_client_instance.list_database_names.side_effect = errors.OperationFailure("Operation error")

    # Expect a RuntimeError with a specific message
    with pytest.raises(RuntimeError, match="MongoDB operation error: Operation error"):
        get_mongo_collection("test_db", "test_collection", "mongodb://localhost:27017")
