from fastapi import Depends, APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks, Request, Form
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Any, Optional
from minio import Minio
import logging
import urllib.parse
import io
from pydantic import BaseModel
from .dependencies import FileInfo, FileMetadata, validate_upload, validate_object_key, get_minio_client, get_pg_client
from .embedding_utils import process_document_embeddings
from .config import CUSTOM_CORPUS_BUCKET as BUCKET_NAME
from .config import EMBED_ON

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage", tags=["storage"])

class Response(BaseModel):
    message: str
    fileinfo: FileInfo

class FolderRequest(BaseModel):
    folder_name: str
    folder_path: Optional[str] = None
    
class FolderResponse(BaseModel):
    message: str
    folder_info: dict

@router.post("/create_folder")
async def create_folder(
    request: FolderRequest,
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> FolderResponse:
    """Create a virtual folder in MinIO storage"""
    logger.info(f"Create folder endpoint triggered: {request.folder_name} in path {request.folder_path}")
    
    try:
        # Build the full folder path
        folder_path = ""
        if request.folder_path:
            folder_path = request.folder_path.strip('/') + '/'
        
        # Full path including the new folder name
        full_path = f"{folder_path}{request.folder_name}/"
        
        # Create an empty placeholder file to represent the folder
        # MinIO doesn't have real folders, so we use a placeholder object
        placeholder_key = f"{full_path}.folder"
        
        # Upload an empty file as a placeholder
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=placeholder_key,
            data=io.BytesIO(b''),  # Empty content
            length=0,  # Content length (zero)
            content_type="application/octet-stream",
            metadata={
                "folder_name": request.folder_name
            }
        )
        
        logger.info(f"Folder created successfully: {full_path}")
        
        return FolderResponse(
            message="Folder created successfully",
            folder_info={
                "name": request.folder_name,
                "path": full_path
            }
        )
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error creating folder: {str(e)}"
        )

@router.post("/upload")
async def upload_document(
    request: Request,
    uploadinfo: Annotated[UploadFile, Depends(validate_upload)],
    background_tasks: BackgroundTasks,
    folder_path: str = Form(None),  # Add folder_path parameter
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None,
    pgvector_client: Annotated[Any, Depends(get_pg_client)] = None
) -> Response:
    """Upload a document to MinIO storage and start embedding creation in background"""
    logger.info(f"Upload endpoint triggered with folder_path: {folder_path}")

    fileinfo = uploadinfo.fileinfo
    
    # If folder_path is provided, update the object_key to include the folder path
    if folder_path:
        # Clean up the folder path and add to object key
        folder_path = folder_path.strip('/') + '/'  # Ensure it has trailing slash but no leading slash
        # Update object key with folder path prefix
        fileinfo.object_key = f"{folder_path}{fileinfo.object_key}"
        logger.info(f"Updated object key with folder path: {fileinfo.object_key}")

    # File is a duplicate, no need to reupload
    # TODO: in the scenario where multiple users try to upload the same file,
    # we don't want to store the same file twice but we do want to make sure the
    # user has access to the file with their credentials and metadata.
    # Return object key (hash) and metadata
    if uploadinfo.duplicate:
        logger.info("File is a duplicate, no need to reupload")
        return Response(
            message="File uploaded successfully", # Abstract duplicate checking from user
            fileinfo=fileinfo
        )
    
    try:
        # Upload directly to MinIO using put_object
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=fileinfo.object_key,
            data=fileinfo.file.file,
            length=fileinfo.file_length,
            content_type=fileinfo.metadata.content_type,
            metadata={
                "file_name": fileinfo.metadata.file_name,
                "content_type": fileinfo.metadata.content_type
            }
        )
        
        logger.info(f"File uploaded successfully: {fileinfo.metadata.file_name}")

        # Get model path from app state
        if EMBED_ON:
            model_path = request.app.state.model_path
            if not model_path:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Model path not set in application state"
                )

            # Add embedding creation as background task
            background_tasks.add_task(
                process_document_embeddings,
                minio_client=minio_client,
                pgvector_client=pgvector_client,
                bucket_name=BUCKET_NAME,
                object_key=fileinfo.object_key,
                model_path=model_path
            )
            
            logger.info(f"Started background embedding creation for: {fileinfo.metadata.file_name}")

        # Don't return file data in response
        fileinfo.file = None
        fileinfo.file_length = None

        return Response(
            message="File uploaded successfully, embeddings being generated in background",
            fileinfo=fileinfo
        )
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
    logger.info(f"Remove endpoint triggered for object: {fileinfo.object_key}")

    try:
        # Remove the object
        minio_client.remove_object(
            BUCKET_NAME,
            fileinfo.object_key
        )

        logger.info(f"File removed successfully: {fileinfo.object_key}")

        return Response(
            message="File removed successfully",
            fileinfo=fileinfo
        )
    except Exception as e:
        logger.error(f"Error removing file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing file: {str(e)}"
        )

@router.get("/serve/{object_key:path}")
async def serve_file(
    object_key: str,
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> StreamingResponse:
    """Serve a file from MinIO storage"""
    # URL decode the object_key to handle properly encoded paths with slashes
    object_key = urllib.parse.unquote(object_key)
    logger.info(f"Serve endpoint triggered for object: {object_key}")
    
    try:
        # Validate object exists
        try:
            # Get file metadata from MinIO
            stat = minio_client.stat_object(BUCKET_NAME, object_key)
            
            # Extract metadata
            metadata = FileMetadata(
                file_name=stat.metadata.get("x-amz-meta-file_name", object_key),
                content_type=stat.metadata.get("x-amz-meta-content_type", "application/octet-stream")
            )
        except Exception as e:
            logger.error(f"Object validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
            
        # Get file data from MinIO
        data = minio_client.get_object(BUCKET_NAME, object_key)
        
        return StreamingResponse(
            data.stream(),
            media_type=metadata.content_type,
            headers={
                'Content-Disposition': f'inline; filename="{metadata.file_name}"',
                'Content-Type': metadata.content_type
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
            
            files.append(
                FileInfo(
                    object_key=obj.object_name,
                    metadata=FileMetadata(
                        file_name=stat.metadata.get("x-amz-meta-file_name", obj.object_name),
                        content_type=stat.metadata.get("x-amz-meta-content_type", "application/octet-stream")
                    )
                )
            )
        
        return files
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )