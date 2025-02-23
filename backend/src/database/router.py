from fastapi import Depends, APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
import io
from typing import List, Annotated
from minio import Minio
import logging
from pydantic import BaseModel
from .dependencies import BUCKET_NAME, FileInfo, validate_upload, validate_object_key, get_minio_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage", tags=["storage"])

class Response(BaseModel):
    message: str
    fileinfo: FileInfo

@router.post("/upload")
async def upload_document(
    fileinfo: Annotated[UploadFile, Depends(validate_upload)],
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> Response:
    """Upload a document to MinIO storage"""
    logger.info("Upload endpoint triggered")

    # File is a duplicate, no need to reupload
    # Return object key (hash) and metadata
    if "file_data" not in fileinfo:
        return {
            "message": "File is a duplicate, no need to reupload",
            "fileinfo": fileinfo
        }
    
    try:
        # Upload directly to MinIO using put_object
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=fileinfo["object_key"],
            data=io.BytesIO(fileinfo["file_data"]),
            length=len(fileinfo["file_data"]),
            content_type=fileinfo["metadata"]["content_type"],
            metadata=fileinfo["metadata"]
        )
        
        logger.info(f"File uploaded successfully: {fileinfo['metadata']['file_name']}")

        # Don't return file data in response
        del fileinfo["file_data"]

        return {
            "message": "File uploaded successfully",
            "fileinfo": fileinfo
        }
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )

@router.delete("/remove/{object_key}")
async def remove_document(
    fileinfo: Annotated[str, Depends(validate_object_key)],
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> Response:
    """Remove a document from MinIO storage"""
    logger.info(f"Remove endpoint triggered for object: {fileinfo['object_key']}")

    try:
        # Remove the object
        minio_client.remove_object(
            BUCKET_NAME,
            fileinfo["object_key"]
        )

        logger.info(f"File removed successfully: {fileinfo['object_key']}")

        return {
            "message": "File removed successfully",
            "fileinfo": fileinfo
        }
    except Exception as e:
        logger.error(f"Error removing file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing file: {str(e)}"
        )

@router.get("/serve/{object_key}")
async def serve_file(
    fileinfo: Annotated[str, Depends(validate_object_key)],
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> StreamingResponse:
    """Serve a file from MinIO storage"""
    logger.info(f"Serve endpoint triggered for object: {fileinfo['object_key']}")
    try:
        # Get file data from MinIO
        data = minio_client.get_object(BUCKET_NAME, fileinfo["object_key"])
        
        return StreamingResponse(
            data.stream(),
            media_type=fileinfo["metadata"]["content_type"],
            headers={
                'Content-Disposition': f'inline; filename="{fileinfo["metadata"]["file_name"]}"',
                'Content-Type': fileinfo["metadata"]["content_type"]
            }
        )
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )

@router.get("/list")
async def list_files(
    prefix: str = None,
    recursive: bool = True,
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> List[FileInfo]:
    """List all files in MinIO storage"""
    logger.info(f"List endpoint triggered with prefix: {prefix}")
    try:
        objects = minio_client.list_objects(BUCKET_NAME, prefix=prefix, recursive=recursive)
        files = []
        
        for obj in objects:
            # Get metadata for each object
            stat = minio_client.stat_object(BUCKET_NAME, obj.object_name)
            
            # NOTE: this is a little ugly, but that's how we can get the original metadata from stat
            files.append({
                "object_key": obj.object_name,
                "metadata": {
                    "file_name": stat.metadata["x-amz-meta-file_name"],
                    "content_type": stat.metadata["x-amz-meta-content_type"]
                }
            })
        
        return files
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )