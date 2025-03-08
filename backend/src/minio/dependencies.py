from fastapi import Depends, HTTPException, status, UploadFile, Form, File
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel
from functools import lru_cache
from typing import Annotated, Optional
from .config import get_minio_settings, BUCKET_NAME, MODELS_BUCKET
import logging
import hashlib

logger = logging.getLogger(__name__)

class FileMetadata(BaseModel):
    file_name: str
    content_type: str
    # TODO: add other relevant metadata as needed

class FileInfo(BaseModel):
    file: Optional[UploadFile] = None
    file_length: Optional[int] = None
    object_key: str
    metadata: Optional[FileMetadata] = None

class UploadInfo(BaseModel):
    duplicate: bool
    fileinfo: FileInfo

@lru_cache()
def get_minio_client() -> Minio:
    """
    Creates and returns a MinIO client instance.
    Cached to avoid creating multiple instances.
    """
    try:
        settings = get_minio_settings()
        client = Minio(
            settings['url'],
            access_key=settings['access_key'],
            secret_key=settings['secret_key'],
            secure=settings['secure']
        )
        
        # Ensure bucket exists
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            logger.info(f"Created bucket: {BUCKET_NAME}")

        if not client.bucket_exists(MODELS_BUCKET):
            client.make_bucket(MODELS_BUCKET)
            logger.info(f"Created bucket: {MODELS_BUCKET}")

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

    # TODO: file validation and cleaning
    return file

async def validate_upload(
    file: UploadFile = File(...),
    folder_path: str = Form(None),  # Add folder_path parameter
    minio_client: Minio = Depends(get_minio_client)
) -> UploadInfo:
    """
    Validates an uploaded file, including checking if it is a duplicate.
    Returns the relevant file content and metadata.
    Raises HTTPException if invalid.
    """
    # Read file and compute hash
    file_data = await file.read()
    file_hash = hashlib.sha256(file_data).hexdigest()
    file_length = len(file_data)

    await file.seek(0)

    metadata = FileMetadata(
        file_name=file.filename,
        content_type=file.content_type
    )

    # Check if file with same hash already exists
    try:
        minio_client.stat_object(BUCKET_NAME, file_hash)
        return UploadInfo(
            duplicate=True,
            fileinfo=FileInfo(
                object_key=file_hash,
                metadata=metadata
            )
        )
    except:
        pass

    return UploadInfo(
        duplicate=False,
        fileinfo=FileInfo(
            file=file,
            file_length=file_length,
            object_key=file_hash,
            metadata=metadata
        )
    )