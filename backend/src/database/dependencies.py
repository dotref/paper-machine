from fastapi import Depends, HTTPException, status, UploadFile
from minio import Minio
from minio.error import S3Error
import psycopg2
import os
import glob
from functools import lru_cache
import logging
from typing import Annotated, Optional, Any
from pydantic import BaseModel
import hashlib
from pathlib import Path
import tempfile
from .embedding_utils import upload_model_to_minio, download_model_from_minio, create_embeddings, save_embeddings_to_vectordb
from .config import CUSTOM_CORPUS_BUCKET as BUCKET_NAME
from .config import VALID_CONTENT_TYPES, MODELS_BUCKET, MODEL_CACHE_DIR, get_minio_settings, get_postgres_settings

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

@lru_cache
def get_pg_client() -> Any:
    """
    Creates and returns a Postgres client instance.
    Cached to avoid creating multiple instances.
    """

    try:
        settings = get_postgres_settings()
        connection = psycopg2.connect(
            host=settings['host'], 
            database=settings['database'], 
            user=settings['user'], 
            password=settings['password'], 
            port=settings['port']
        )

        return connection
    except KeyError as e:
        logger.error(f"Missing environment variable: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Postgres configuration error: missing {e}"
        )
    except psycopg2.Error as e:
        logger.error(f"Postgres error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Postgres error: {str(e)}"
        )

# def upload_model(
#     embedding_model: str,
#     embedding_model_revision: str = "latest",
#     minio_client: Annotated[Minio, Depends(get_minio_client)] = None
# ) -> None:
#     """
#     Uploads a model to MinIO if it doesn't already exist.
#     """
#     try:
#         # Check if model already exists in MinIO
#         model_path = f"models--{embedding_model}--{embedding_model_revision}"
#         objects = minio_client.list_objects(MODELS_BUCKET, prefix=f"{model_path}/snapshots/", recursive=True)
        
#         # Convert to list to check if there are any objects
#         if len(list(objects)) > 0:
#             logger.info(f"Model {embedding_model} already exists in MinIO")
#             return
            
#         # Model doesn't exist, proceed with upload
#         upload_model_to_minio(minio_client, MODELS_BUCKET, embedding_model, embedding_model_revision)
#         logger.info(f"Uploaded model: {embedding_model}")
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to upload model: {str(e)}"
#         )

# def download_model(
#     embedding_model: str,
#     embedding_model_revision: str = "latest",
#     minio_client: Annotated[Minio, Depends(get_minio_client)] = None,
# ) -> str:
#     """
#     Download a model from MinIO. Calls upload_model to check if the model exists in MinIO.
#     Returns a local path to the downloaded model.
#     """
#     try:
#         upload_model(embedding_model, embedding_model_revision)
#         # Get the user name and the model name
#         user_name, model_name = embedding_model.split('/')
#         model_path_name = f'models--{user_name}--{model_name}'
#         full_model_local_path = os.path.join(MODEL_CACHE_DIR, model_path_name, 'snapshots', embedding_model_revision)
        
#         # If model exists locally and directory is not empty, use it
#         if os.path.exists(full_model_local_path) and any(os.scandir(full_model_local_path)):
#             logger.info(f"Using locally cached model at {full_model_local_path}")
#             return full_model_local_path
            
#         # Otherwise download from MinIO
#         return download_model_from_minio(minio_client, MODELS_BUCKET, embedding_model, embedding_model_revision)
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to download model: {str(e)}"
#         )

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
    file: Annotated[UploadFile, Depends(validate_file)],
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
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
        return FileInfo(
            object_key=object_key,
            metadata=FileMetadata(
                file_name=stat.metadata.get("x-amz-meta-file_name", object_key),
                content_type=stat.metadata.get("x-amz-meta-content_type", "application/octet-stream")
            )
        )
    except:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found"
        )