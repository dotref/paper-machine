from fastapi import Depends, HTTPException, status, UploadFile
from minio import Minio
from minio.error import S3Error
import os
from functools import lru_cache
import logging
from typing import Annotated, Optional
from pydantic import BaseModel
import hashlib

logger = logging.getLogger(__name__)

BUCKET_NAME = "custom-corpus"
VALID_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/json"
    # TODO: add more supported content types as needed
}

class FileMetadata(BaseModel):
    file_name: str
    content_type: str
    # TODO: add other relevant metadata as needed

class FileInfo(BaseModel):
    file_data: Optional[str] = None
    object_key: str
    metadata: Optional[FileMetadata] = None

@lru_cache()
def get_minio_client() -> Minio:
    """
    Creates and returns a MinIO client instance.
    Cached to avoid creating multiple instances.
    """
    try:
        client = Minio(
            os.environ['MINIO_URL'],
            access_key=os.environ['MINIO_ACCESS_KEY'],
            secret_key=os.environ['MINIO_SECRET_KEY'],
            secure=os.environ['MINIO_SECURE'].lower() == 'true'
        )
        
        # Ensure bucket exists
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            logger.info(f"Created bucket: {BUCKET_NAME}")
        
        return client
    except KeyError as e:
        logger.error(f"Missing environment variable: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MinIO configuration error: missing {e}"
        )
    except S3Error as e:
        logger.error(f"MinIO error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MinIO error: {str(e)}"
        )

async def validate_file(
    file: UploadFile
) -> UploadFile:
    """
    Validates a file and returns it.
    Raises HTTPException if invalid.
    """
    if file.content_type not in VALID_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")
    return file

async def validate_upload(
    file: Annotated[UploadFile, Depends(validate_file)],
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> FileInfo:
    """
    Validates an uploaded file, including checking if it is a duplicate.
    Returns the relevant file content and metadata.
    Raises HTTPException if invalid.
    """
    # Read file and compute hash
    file_data = await file.read()
    file_hash = hashlib.sha256(file_data).hexdigest()

    metadata = {
        "file_name": file.filename,
        "content_type": file.content_type,
    }

    # Check if file with same hash already exists
    try:
        minio_client.stat_object(BUCKET_NAME, file_hash)
        return {
            "object_key": file_hash,
            "metadata": metadata
        }
    except:
        pass

    return {
        "file_data": file_data,
        "object_key": file_hash,
        "metadata": metadata
    }

async def validate_object_key(
    object_key: str,
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> FileInfo:
    """
    Validates whether an object exists in MinIO storage.
    Returns the object key if valid.
    Raises HTTPException if invalid.
    """
    try:
        stat = minio_client.stat_object(BUCKET_NAME, object_key)
        # NOTE: this is a little ugly, but that's how we can get the original metadata from stat
        return {
            "object_key": object_key,
            "metadata": {
                "file_name": stat.metadata["x-amz-meta-file_name"],
                "content_type": stat.metadata["x-amz-meta-content_type"]
            }
        }
    except:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found"
        )