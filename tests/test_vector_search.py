from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_successful_upload():
    """Test a successful retrival."""

    response = client.post("/vector_search/query", json={
        "query": "what is beer?",
        "uri": "",
        "db_name": "",
        "collection_name": ""
    })

    print("RESULT:  ",response.json().get("result"))

    assert response.status_code == 200
    assert response.json().get("result") == "Query successful."

def test_invalid_file_type():
    """Test when the provided query is not coherent with the collection."""

    response = client.post("/vector_search/query", json={
        "query": "what is paper?",
        "uri": "",
        "db_name": "",
        "collection_name": ""
    })

    assert response.status_code == 400
    assert response.json() == {"detail": "No results found. Please write a coherent query."}

def test_pdf_without_text():
    """Test when the query does not contain any text or is too short."""

    response = client.post("/vector_search/query", json={
        "query": "beer",
        "uri": "",
        "db_name": "",
        "collection_name": ""
    })

    assert response.status_code == 400
    assert response.json() == {"detail": "Query is too short, please contextualize more."}
