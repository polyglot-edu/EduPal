from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_successful_upload():
    """Test a successful file upload."""

    response = client.post("/upload/upload", json={
        "file": "C:/Users/elpip/Desktop/E4E/OERs/valid_beer.pdf",
        "uri": "",
        "db_name": "",
        "collection_name": ""
    })

    assert response.status_code == 200
    assert response.json() == {"results": "Upload successful."}

def test_invalid_file_type():
    """Test when the provided file is not a PDF."""

    response = client.post("/upload/upload", json={
        "file": "C:/Users/elpip/Desktop/E4E/OERs/invalid.txt",
        "uri": "",
        "db_name": "",
        "collection_name": ""
    })

    assert response.status_code == 400
    assert response.json() == {"detail": "Only PDF files are accepted"}

def test_pdf_without_text():
    """Test when the PDF file does not contain any text."""

    response = client.post("/upload/upload", json={
        "file": "C:/Users/elpip/Desktop/E4E/OERs/empty.pdf",
        "uri": "",
        "db_name": "",
        "collection_name": ""
    })

    assert response.status_code == 400
    assert response.json() == {"detail": "Document is empty"}

def test_too_short_document():
    """Test when the PDF file contains only a few words."""

    response = client.post("/upload/upload", json={
        "file": "C:/Users/elpip/Desktop/E4E/OERs/short_cl.pdf",
        "uri": "",
        "db_name": "",
        "collection_name": ""
    })

    assert response.status_code == 400
    assert response.json() == {"detail": "Document is too short"}
