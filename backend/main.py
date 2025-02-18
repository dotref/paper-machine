from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
from typing import Dict, List
import os
from pathlib import Path
from minio import Minio
from minio.error import S3Error
import uvicorn
import logging

from pyprojroot import here
from dotenv import load_dotenv

root_dir = here()

# Load environment variables
load_dotenv(os.path.join(root_dir, 'embedding_subsystem', 'minio.env'))

# Configure MinIO client
client = Minio(
    os.environ['MINIO_URL'],
    access_key=os.environ['MINIO_ACCESS_KEY'],
    secret_key=os.environ['MINIO_SECRET_KEY'],
    secure=os.environ['MINIO_SECURE'].lower() == 'true'
)

BUCKET_NAME = "custom-corpus"
UPLOAD_FOLDER = "backend/uploads"
ALLOWED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.txt': 'text/plain'
}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/health")
async def health_check() -> Dict[str, str]:
    logger.info("Health check requested")
    return {"status": "healthy"}

# Index Route
@app.get("/")
async def index() -> Dict[str, str]:
    logger.info("Index page accessed")
    return {
        "message": "Welcome to the backend API"
    }

# File Upload Endpoint
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    logger.info("Upload endpoint triggered")
    
    if file.filename == "":
        logger.info("No filename provided")
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        logger.info(f"Unsupported file type: {file_ext}")
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        client.fput_object(BUCKET_NAME, file.filename, file_path)
        os.remove(file_path)
        
        logger.info(f"File uploaded successfully: {file.filename}")
        return {"message": "File uploaded successfully", "filename": file.filename, "file_type": file_ext[1:].upper()}
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

# File Removal Endpoint
@app.delete("/remove/{filename}")
async def remove_document(filename: str):
    logger.info(f"Remove endpoint triggered for file: {filename}")
    try:
        client.remove_object(BUCKET_NAME, filename)
        logger.info(f"File removed successfully: {filename}")
        return {"message": "File removed successfully", "status": "success"}
    except Exception as e:
        logger.error(f"Error removing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error removing file: {str(e)}")

# Serve Uploaded Files
@app.get("/uploads/{filename}")
async def serve_file(filename: str):
    try:
        response = client.get_object(BUCKET_NAME, filename)
        file_stream = io.BytesIO(response.read())
        
        extension = os.path.splitext(filename)[1].lower()
        media_type = ALLOWED_EXTENSIONS.get(extension, 'application/octet-stream')
        
        # Return response without Content-Disposition header to display in browser
        return StreamingResponse(file_stream, media_type=media_type)
    except S3Error as e:
        logger.error(f"Error fetching file from MinIO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching file: {str(e)}")

# List Files Endpoint
@app.get("/files")
async def list_files():
    try:
        logger.info(f"Attempting to list objects in bucket: {BUCKET_NAME}")
        objects = client.list_objects(BUCKET_NAME, recursive=True)
        files = [obj.object_name for obj in objects]
        logger.info(f"List endpoint triggered: {files}")
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)