# FastAPI Upload API Documentation

## Overview

This API allows users to upload PDF files and perform semantic chunking on them. The uploaded documents are then processed and stored in a MongoDB collection. The API provides an endpoint to upload the file, with optional parameters for MongoDB connection details. If these details are not provided, environment variables are used as a fallback.

## Endpoints

### POST /upload/upload

#### Description:
Uploads a file (PDF) and performs semantic chunking. The file will be uploaded to the specified MongoDB database and collection.

#### Request Body:

```json
{
  "file": "string",                 // The path of the PDF file to upload
  "uri": "string",                  // (Optional) MongoDB connection URI
  "db_name": "string",              // (Optional) MongoDB database name
  "collection_name": "string"      // (Optional) MongoDB collection name
}
```
### Request Body Fields

- **file**: Required. The path to the PDF file to upload.
- **uri**: Optional. The MongoDB connection URI. If not provided, environment variables will be used.
- **db_name**: Optional. The name of the MongoDB database. If not provided, a default value of `edu_db` will be used.
- **collection_name**: Optional. The name of the MongoDB collection. If not provided, a default value of `materials` will be used.

### Responses

#### 200 OK:
- **Successful Call**: Returns a JSON response with a status code of 200 and a message indicating the successful upload.

#### Error Handling
- **File is not a PDF**: Returns a 400 Bad Request with an error message: "Only PDF files are accepted"
- **File is empty**: Returns a 400 Bad Request with an error message: "Document is empty"
- **File is too short**: Returns a 400 Bad Request with an error message "Document is too short"
- **Not Found**: Returns a 404 Not Found
- **Validation Error**: Returns a 422 Unprocessable Entity
- **Internal Server Error**: Returns a 500 Internal Server Error
