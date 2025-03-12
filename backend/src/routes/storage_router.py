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

from ..auth.utils import get_current_user

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
    fileinfo: FileInfo

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
    user_id = current_user["id"]
    # user_prefix = get_user_file_prefix(user_id)
    logger.info(f"Upload endpoint triggered by user {user_id}")

    fileinfo = uploadinfo.fileinfo
    
    # Add user prefix to the object key to ensure user-specific storage
    # If folder_path is provided, it will be within the user's folder
    # if folder_path:
    #     # Clean up the folder path
    #     folder_path = folder_path.strip('/')
    #     # Update object key with user prefix and folder path
    #     fileinfo.object_key = f"{user_prefix}{folder_path}/{fileinfo.object_key.split('/')[-1]}"
    # else:
    #     # Just add user prefix
    #     fileinfo.object_key = f"{user_prefix}{fileinfo.object_key.split('/')[-1]}"
    # logger.info(f"Updated object key with user prefix: {fileinfo.object_key}")

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
                
                logger.info(f"Started background embedding creation for: {fileinfo.metadata.file_name}")
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error uploading file to MinIO")
    
    try:
        # Record file metadata in database
        query = """
        INSERT INTO user_files (user_id, object_key, original_filename, content_type)
        VALUES (:user_id, :object_key, :original_filename, :content_type)
        ON CONFLICT (user_id, object_key) DO NOTHING
        RETURNING id
        """
        values = {
            "user_id": user_id,
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
    user_id = current_user["id"]
    # user_prefix = get_user_file_prefix(user_id)
    logger.info(f"Remove endpoint triggered by user {user_id} for object: {object_key}")

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
        WHERE user_id = :user_id AND object_key = :object_key
        """
        
        result = await db.execute(
            query=query, 
            values={"user_id": user_id, "object_key": object_key}
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
    
    user_id = current_user["id"]
    # user_prefix = get_user_file_prefix(user_id)
    logger.info(f"Serve endpoint triggered by user {user_id} for object: {object_key}")
    
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
        WHERE user_id = :user_id AND object_key = :object_key
        """
        
        file_record = await db.fetch_one(
            query=query, 
            values={"user_id": user_id, "object_key": object_key}
        )

        if not file_record:
            logger.warning(f"Unauthorized access attempt. User {user_id} doesn't have access to object {object_key}")
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
async def temp_list_files(
    current_user: dict = Depends(get_current_user),
    db: Annotated[Database, Depends(get_db)] = None
):
    """
    List all files user has access to.
    NOTE: At the moment, there is no folder structure in object store due to
    the implementation of file and embedding deduplication.
    Folder structure may need to be client-side
    """
    user_id = current_user["id"]

    query = """
    SELECT *
    FROM user_files
    WHERE user_id = :user_id
    """
    values = {"user_id": user_id}
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

async def list_files(
    folder_path: Optional[str] = Query(None),
    recursive: bool = True,
    current_user: dict = Depends(get_current_user),
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
) -> List[Dict]:
    """List all files in user's storage area"""
    user_id = current_user["id"]
    user_prefix = get_user_file_prefix(user_id)
    
    # Ensure we're only listing files in the user's directory
    if folder_path:
        # Combine user prefix with requested folder path
        list_prefix = f"{user_prefix}{folder_path.lstrip('/')}"
    else:
        list_prefix = user_prefix
        
    logger.info(f"List endpoint triggered by user {user_id} with prefix: {list_prefix}")
    
    try:
        # Get all objects including folders
        objects = list(minio_client.list_objects(BUCKET_NAME, prefix=list_prefix, recursive=recursive))
        
        # Collect folder paths (for empty folders)
        folders = set()
        
        # Scan objects to find potential folder paths
        for obj in objects:
            if obj.object_name.endswith('.folder'):
                # Direct folder marker
                folder_path = obj.object_name[:-7]  # Remove '.folder'
                folders.add(folder_path)
            elif '/' in obj.object_name.replace(list_prefix, '', 1):
                # Extract parent folders from object paths
                path_parts = obj.object_name.split('/')
                # Build each ancestor path
                for i in range(1, len(path_parts)):
                    folder_path = '/'.join(path_parts[:i]) + '/'
                    if folder_path.startswith(user_prefix):
                        folders.add(folder_path)
        
        files = []
        
        # Process regular files
        for obj in objects:
            # Skip folder markers for cleaner output
            if obj.object_name.endswith('.folder'):
                continue
                
            # Get relative path (remove user prefix for cleaner output)
            relative_path = obj.object_name.replace(user_prefix, '')
            
            try:
                # Get metadata for each object
                stat = minio_client.stat_object(BUCKET_NAME, obj.object_name)
                filename = stat.metadata.get("x-amz-meta-file_name", obj.object_name.split('/')[-1])
                content_type = stat.metadata.get("x-amz-meta-content_type", "application/octet-stream")
            except:
                filename = obj.object_name.split('/')[-1]
                content_type = "application/octet-stream"
            
            files.append({
                "object_key": obj.object_key if hasattr(obj, 'object_key') else obj.object_name,
                "metadata": {
                    "file_name": filename,
                    "relative_path": relative_path,
                    "content_type": content_type,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
                }
            })
        
        # Add explicit folder entries
        for folder_path in folders:
            # Skip if this is the current listing prefix
            if folder_path == list_prefix:
                continue
                
            # Get folder name (last part of the path)
            folder_name = folder_path.rstrip('/').split('/')[-1]
            # Get relative path
            relative_path = folder_path.replace(user_prefix, '')
            
            files.append({
                "object_key": folder_path + ".folder",
                "metadata": {
                    "file_name": folder_name,
                    "relative_path": relative_path,
                    "content_type": "application/directory",  # Special type for folders
                    "size": 0,
                    "last_modified": None
                }
            })
        
        return files
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )

@router.post("/create-folder")
async def temp_create_folder_endpoint(
    current_user: dict = Depends(get_current_user),
):
    logger.info(f"User {current_user['id']} triggered folder creation")

async def create_folder_endpoint(
    folder_name: str = Form(...),
    parent_folder: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None
):
    """Create a folder in user's storage area"""
    user_id = current_user["id"]
    logger.info(f"User {user_id} creating folder: {folder_name} in {parent_folder or 'root'}")
    
    try:
        # Create folder
        folder_path = create_folder(
            folder_name=folder_name,
            user_id=user_id,
            parent_folder=parent_folder
        )
        
        # Remove user prefix for client response
        user_prefix = get_user_file_prefix(user_id)
        relative_path = folder_path.replace(user_prefix, "")
        
        return {
            "message": "Folder created successfully",
            "folder_info": {
                "name": folder_name,
                "path": relative_path,
                "full_path": folder_path
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Folder creation failed: {str(e)}"
        )

@router.post("/remove-folder")
async def temp_remove_folder_endpoint(
    current_user: dict = Depends(get_current_user),
):
    logger.info(f"User {current_user['id']} triggered folder removal")

async def remove_folder_endpoint(
    request: RemoveFolderRequest,
    current_user: dict = Depends(get_current_user),
    minio_client: Annotated[Minio, Depends(get_minio_client)] = None,
    db = Depends(get_db)
) -> RemoveFolderResponse:
    """Remove a folder and all its contents from user's storage area"""
    user_id = current_user["id"]
    user_prefix = get_user_file_prefix(user_id)
    
    folder_path = request.folder_path.strip('/')
    if not folder_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder path is required"
        )
    
    # Make sure the folder path includes the user prefix
    if not folder_path.startswith(user_prefix.rstrip('/')):
        folder_path = f"{user_prefix}{folder_path}"
    
    # Add trailing slash to match all objects with this prefix
    prefix = f"{folder_path}/"
    logger.info(f"User {user_id} removing folder: {prefix}")
    
    # Verify this folder belongs to the user
    if not folder_path.startswith(user_prefix):
        logger.warning(f"Unauthorized folder removal attempt. Folder {folder_path} does not belong to user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove this folder"
        )
    
    try:
        # List all objects with the folder prefix
        objects = list(minio_client.list_objects(BUCKET_NAME, prefix=prefix, recursive=True))
        
        # Also include the folder marker if it exists
        folder_marker_objects = list(minio_client.list_objects(
            BUCKET_NAME, 
            prefix=f"{prefix}.folder", 
            recursive=False
        ))
        objects.extend(folder_marker_objects)
        
        # If no objects found, folder doesn't exist
        if not objects:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder '{folder_path}' not found or is empty"
            )
        
        # Remove all objects in the folder
        removed_objects = []
        for obj in objects:
            # Remove from MinIO
            minio_client.remove_object(BUCKET_NAME, obj.object_name)
            
            # Also remove from database if it's a file
            if not obj.object_name.endswith("/.folder"):
                await db.execute(
                    "DELETE FROM user_files WHERE user_id = :user_id AND object_key = :object_key",
                    values={"user_id": user_id, "object_key": obj.object_name}
                )
                
            removed_objects.append(obj.object_name)
            logger.info(f"Removed object: {obj.object_name}")
        
        return RemoveFolderResponse(
            message=f"Folder '{folder_path.replace(user_prefix, '')}' and {len(removed_objects)} objects removed successfully",
            folder_path=folder_path,
            removed_objects=removed_objects
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error removing folder: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing folder: {str(e)}"
        )

# TODO: Error retrieving storage structure: list_files() got an unexpected keyword argument 'user_id'
@router.get("/storage-structure")
async def get_storage_structure(
    current_user: dict = Depends(get_current_user)
):
    """TODO: Get a breakdown of the user's storage structure for diagnostic purposes"""
    try:
        user_id = current_user["id"]
        user_prefix = get_user_file_prefix(user_id)
        
        # Get all objects for this user
        objects = list_files(user_id=user_id)
        
        # Organize by folder structure
        structure: Dict[str, List[Dict[str, Any]]] = {"root": []}
        
        for obj in objects:
            # Skip folder markers for clarity
            if obj.object_name.endswith("/.folder"):
                continue
                
            # Remove user prefix to see relative structure
            relative_path = obj.object_name.replace(user_prefix, "")
            parts = relative_path.split("/")
            
            # Files in root
            if len(parts) == 1:
                structure["root"].append({
                    "name": parts[0],
                    "size": obj.size,
                    "full_path": obj.object_name,
                    "relative_path": relative_path
                })
            else:
                # Files in subfolders
                folder = "/".join(parts[:-1])
                if folder not in structure:
                    structure[folder] = []
                
                structure[folder].append({
                    "name": parts[-1],
                    "size": obj.size,
                    "full_path": obj.object_name,
                    "relative_path": relative_path
                })
        
        return {
            "user_id": user_id,
            "user_prefix": user_prefix,
            "structure": structure
        }
    
    except Exception as e:
        logger.error(f"Diagnostic error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving storage structure: {str(e)}"
        )

@router.get("/debug-file-request/{object_key:path}")
async def debug_file_request(
    object_key: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Debug endpoint for file request issues"""
    # URL decode the object_key for clarity
    decoded_key = urllib.parse.unquote(object_key)
    
    return {
        "status": "success",
        "user_id": current_user["id"],
        "username": current_user["username"],
        "object_key": {
            "received": object_key,
            "decoded": decoded_key
        },
        "auth_header": request.headers.get("authorization", "")[:20] + "...",
        "user_prefix": get_user_file_prefix(current_user["id"])
    }