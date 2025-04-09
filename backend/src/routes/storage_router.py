from fastapi import Depends, APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks, Request, Form, Query
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Any, Optional, Dict
from minio import Minio
import logging
import urllib.parse
from databases import Database
from pydantic import BaseModel

from ..database.dependencies import get_db
from ..database.utils import process_document_embeddings

from ..auth.utils import get_current_user, get_user

from ..minio.config import BUCKET_NAME
from ..minio.dependencies import FileInfo, validate_upload, get_minio_client
from ..minio.utils import (
    upload_file,
    download_file,
    list_files,
    remove_file,
    create_folder,
    get_user_file_prefix
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage", tags=["storage"])

class Response(BaseModel):
    message: str
    fileinfo: Optional[FileInfo] = None

# Add these new models for folder operations
class FolderRequest(BaseModel):
    folder_name: str
    folder_path: Optional[str] = None
    
class FolderResponse(BaseModel):
    message: str
    folder_info: dict

class RemoveFolderRequest(BaseModel):
    folder_path: str

class RemoveFolderResponse(BaseModel):
    message: str
    folder_path: str
    removed_objects: List[str]

class ShareFileRequest(BaseModel):
    object_key: str
    target_username: str

@router.post("/upload")
async def upload_document(
    uploadinfo: Annotated[UploadFile, Depends(validate_upload)],
    request: Request,
    background_tasks: BackgroundTasks,
    # folder_path: str = Form(None),
    current_user: dict = Depends(get_current_user),
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None,
    db: Annotated[Database, Depends(get_db)] = None
) -> Response:
    """Upload a document to user's storage area and start embedding creation in background"""
    username = current_user["username"]
    # user_prefix = get_user_file_prefix(user_id)
    logger.info(f"Upload endpoint triggered by user {username}")

    fileinfo = uploadinfo.fileinfo
    
    # File is not a duplicate, need to reupload
    if not uploadinfo.duplicate:
        logger.info(f"File is not a duplicate, need to upload: {fileinfo.object_key}")
        # Upload directly to MinIO using put_object
        try:
            minio_client.put_object(
                bucket_name=BUCKET_NAME,
                object_name=fileinfo.object_key,
                data=fileinfo.file.file,
                length=fileinfo.file_length,
                content_type=fileinfo.metadata.content_type or "application/octet-stream",
                metadata={
                    "file_name": fileinfo.metadata.file_name,
                    "content_type": fileinfo.metadata.content_type
                }
            )
            
            # Record object upload in database
            query = """
            INSERT INTO objects (object_key, content_type, size)
            VALUES (:object_key, :content_type, :size)
            """
            values = {
                "object_key": fileinfo.object_key,
                "content_type": fileinfo.metadata.content_type or "application/octet-stream",
                "size": fileinfo.file_length
            }
            await db.execute(query=query, values=values)
            logger.info(f"Recorded object upload in database: {fileinfo.object_key}")

            # Get model path from app state
            if request.app.state.embed_on:
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
                    db=db,
                    bucket_name=BUCKET_NAME,
                    object_key=fileinfo.object_key,
                    model_path=model_path
                )

                logger.info(f"[Embedding] 📦 Background task scheduled for {fileinfo.object_key}")
                
                logger.info(f"Started background embedding creation for: {fileinfo.metadata.file_name}")
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error uploading file to MinIO")
    
    try:
        # Record file metadata in database
        query = """
        INSERT INTO user_files (username, object_key, original_filename, content_type)
        VALUES (:username, :object_key, :original_filename, :content_type)
        ON CONFLICT (username, object_key) DO NOTHING
        RETURNING id
        """
        values = {
            "username": username,
            "object_key": fileinfo.object_key,
            "original_filename": fileinfo.metadata.file_name,
            "content_type": fileinfo.metadata.content_type or "application/octet-stream"
        }
        
        file_record = await db.execute(query=query, values=values)
        logger.info(f"File record created in database with ID: {file_record}")
        
        logger.info(f"File uploaded successfully: {fileinfo.metadata.file_name}")

        # Don't return file data in response
        fileinfo.file = None
        fileinfo.file_length = None

        return Response(
            message="File uploaded successfully",
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
    object_key: str,
    current_user: dict = Depends(get_current_user),
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None,
    db = Depends(get_db)
) -> dict:
    """Remove a document from storage"""
    username = current_user["username"]
    # user_prefix = get_user_file_prefix(user_id)
    logger.info(f"Remove endpoint triggered by user {username} for object: {object_key}")

    # Verify the object belongs to this user
    # if not object_key.startswith(user_prefix):
    #     logger.warning(f"Unauthorized removal attempt. Object {object_key} doesn't belong to user {user_id}")
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to remove this file"
    #     )

    try:
        # Remove database record
        query = """
        DELETE FROM user_files 
        WHERE username = :username AND object_key = :object_key
        """
        
        result = await db.execute(
            query=query, 
            values={"username": username, "object_key": object_key}
        )

        logger.info(f"File removed successfully: {object_key}")

        # Remove file if no longer referenced
        query = """
        SELECT count(*) 
        FROM user_files 
        WHERE object_key = :object_key
        """
        result = await db.execute(
            query=query, 
            values={"object_key": object_key}
        )
        if result == 0:
            # Remove the object from MinIO
            minio_client.remove_object(BUCKET_NAME, object_key)

            # Remove the database record
            query = """
            DELETE FROM objects 
            WHERE object_key = :object_key
            """
            await db.execute(
                query=query, 
                values={"object_key": object_key}
            )
        
        return {
            "message": "File removed successfully",
            "object_key": object_key
        }
    except Exception as e:
        logger.error(f"Error removing file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing file: {str(e)}"
        )

@router.get("/serve/{object_key}")
async def serve_file(
    object_key: str,
    current_user: dict = Depends(get_current_user),
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None,
    db = Depends(get_db)
) -> StreamingResponse:
    """Serve a file from storage"""
    # URL decode the object_key to handle properly encoded paths with slashes
    object_key = urllib.parse.unquote(object_key)
    
    username = current_user["username"]
    # user_prefix = get_user_file_prefix(user_id)
    logger.info(f"Serve endpoint triggered by user {username} for object: {object_key}")
    
    # Verify the object belongs to this user

    # if not object_key.startswith(user_prefix) and not object_key.startswith("system/"):
    #     logger.warning(f"Unauthorized access attempt. Object {object_key} doesn't belong to user {user_id}")
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to access this file"
    #     )
    
    try:
        # Lookup file metadata in database
        query = """
        SELECT original_filename, content_type FROM user_files 
        WHERE username = :username AND object_key = :object_key
        """
        
        file_record = await db.fetch_one(
            query=query, 
            values={"username": username, "object_key": object_key}
        )

        if not file_record:
            logger.warning(f"Unauthorized access attempt. User {username} doesn't have access to object {object_key}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this file"
            )
        
        # Get file data from MinIO
        data = minio_client.get_object(BUCKET_NAME, object_key)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return StreamingResponse(
            data.stream(),
            media_type=file_record["content_type"] or "application/octet-stream",
            headers={
                'Content-Disposition': f'inline; filename="{file_record["original_filename"]}"',
                'Content-Type': file_record["content_type"] or "application/octet-stream"
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )

@router.get("/list")
async def list_files(
    current_user: dict = Depends(get_current_user),
    db: Annotated[Database, Depends(get_db)] = None
):
    """
    List all files user has access to.
    NOTE: At the moment, there is no folder structure in object store due to
    the implementation of file and embedding deduplication.
    Folder structure may need to be client-side
    """
    username = current_user["username"]

    query = """
    SELECT *
    FROM user_files
    WHERE username = :username
    """
    values = {"username": username}
    user_files = await db.fetch_all(query=query, values=values)

    files = []
    for entry in user_files:
        query = """
        SELECT *
        FROM objects
        WHERE object_key = :object_key
        """
        values = {"object_key": entry.object_key}
        obj = await db.fetch_one(query=query, values=values)

        files.append({
            "object_key": obj.object_key,
            "metadata": {
                "file_name": entry.original_filename,
                "content_type": obj.content_type,
                "size": obj.size,
                # "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
            }
        })
    return files

@router.post("/share")
async def share_file(
    share_request: ShareFileRequest,
    current_user: dict = Depends(get_current_user),
    db: Annotated[Database, Depends(get_db)] = None
):
    """
    Share a file with another user
    """
    # Check if target user exists
    target_user = await get_user(db, share_request.target_username)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found"
        )

    try:
        # Get file metadata from original user
        query = """
        SELECT *
        FROM user_files
        WHERE username = :username AND object_key = :object_key
        """
        values = {
            "username": current_user["username"],
            "object_key": share_request.object_key
        }
        fileinfo = await db.fetch_one(query=query, values=values)
        if not fileinfo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error retrieving user file"
            )
        
        # Share file with target user
        query = """
        INSERT INTO user_files (username, object_key, original_filename, content_type)
        VALUES (:username, :object_key, :original_filename, :content_type)
        ON CONFLICT (username, object_key) DO NOTHING
        """
        values = {
            "username": share_request.target_username,
            "object_key": fileinfo.object_key,
            "original_filename": fileinfo.original_filename,
            "content_type": fileinfo.content_type or "application/octet-stream"
        }
        
        await db.execute(query=query, values=values)

        return Response(
            message="File shared successfully"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error sharing file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sharing file: {str(e)}"
        )
