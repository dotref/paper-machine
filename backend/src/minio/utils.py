import os
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import logging
from .config import get_minio_settings, BUCKET_NAME

# Set up logging
logger = logging.getLogger(__name__)

# Get MinIO settings from config
minio_settings = get_minio_settings()

# Initialize MinIO client
minio_client = Minio(
    endpoint=minio_settings['url'],
    access_key=minio_settings['access_key'],
    secret_key=minio_settings['secret_key'],
    secure=minio_settings['secure']
)

def initialize_minio():
    """Initialize MinIO with default bucket if it doesn't exist."""
    try:
        if not minio_client.bucket_exists(BUCKET_NAME):
            minio_client.make_bucket(BUCKET_NAME)
            logger.info(f"Created bucket: {BUCKET_NAME}")
    except S3Error as e:
        logger.error(f"Error initializing MinIO: {e}")
        raise

def create_user_bucket(user_id_prefix):
    """Create a user's storage area within the main bucket."""
    try:
        # Create a folder placeholder for the user
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=f"{user_id_prefix}/.folder",
            data=BytesIO(b""),
            length=0,
            content_type="application/octet-stream"
        )
        logger.info(f"User storage area created: {user_id_prefix}")
        return True
    except S3Error as e:
        logger.error(f"Error creating user storage area: {e}")
        return False

def get_user_file_prefix(user_id):
    """Get the proper prefix for user files."""
    return f"user-{user_id}/"

def upload_file(file_data, filename, content_type, user_id=None, folder_path=None):
    """
    Upload a file to MinIO with user-specific path.
    
    Args:
        file_data: File data stream
        filename: Original filename
        content_type: MIME type of file
        user_id: ID of user who owns the file (for user-specific storage)
        folder_path: Optional subfolder path within user's storage
        
    Returns:
        object_key: The object key in MinIO
    """
    try:
        # Determine the object key based on user_id and folder path
        if user_id:
            # Use user-specific path
            user_prefix = get_user_file_prefix(user_id)
            
            if folder_path:
                # Ensure folder path doesn't have leading/trailing slashes
                folder_path = folder_path.strip('/')
                object_key = f"{user_prefix}{folder_path}/{filename}"
            else:
                object_key = f"{user_prefix}{filename}"
        else:
            # For system files or when no user is specified (should be rare)
            if folder_path:
                folder_path = folder_path.strip('/')
                object_key = f"system/{folder_path}/{filename}"
            else:
                object_key = f"system/{filename}"
        
        logger.info(f"Uploading file with object key: {object_key}")
        
        # Upload the file to MinIO
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_key,
            data=file_data,
            length=-1,  # Let MinIO determine size
            content_type=content_type,
            metadata={
                "file_name": filename,
                "content_type": content_type
            }
        )
        
        logger.info(f"File uploaded successfully: {object_key}")
        return object_key
    
    except S3Error as e:
        logger.error(f"Error uploading file: {e}")
        raise e

def download_file(object_key, user_id=None):
    """
    Download a file from MinIO, optionally checking user ownership.
    
    Args:
        object_key: The object key in MinIO
        user_id: ID of user requesting access (for authorization)
        
    Returns:
        file_data: The file data stream or None if access is denied
    """
    try:
        # If user_id is provided, verify access permission
        if user_id is not None:
            user_prefix = get_user_file_prefix(user_id)
            
            # Check if the object belongs to this user
            if not object_key.startswith(user_prefix) and not object_key.startswith("system/"):
                logger.warning(f"Access denied: {object_key} doesn't belong to user {user_id}")
                return None
                
        # Get the object
        return minio_client.get_object(BUCKET_NAME, object_key)
    
    except S3Error as e:
        logger.error(f"Error downloading file: {e}")
        return None

def list_files(prefix=None, user_id=None, recursive=True):
    """
    List files in MinIO, filtered by user if specified.
    
    Args:
        prefix: Optional prefix to filter objects
        user_id: ID of user to filter by
        recursive: Whether to list files recursively
        
    Returns:
        List of MinIO objects
    """
    try:
        # If user_id is provided, ensure we only list their files
        if user_id is not None:
            user_prefix = get_user_file_prefix(user_id)
            
            # If a specific prefix was provided, combine with user prefix
            if prefix:
                list_prefix = f"{user_prefix}{prefix.lstrip('/')}"
            else:
                list_prefix = user_prefix
        else:
            # Without user_id, use provided prefix or empty string
            list_prefix = prefix or ""
            
        logger.info(f"Listing files with prefix: {list_prefix}")
            
        # List objects
        objects = list(minio_client.list_objects(
            bucket_name=BUCKET_NAME,
            prefix=list_prefix,
            recursive=recursive
        ))
        
        # Log the number of objects found
        logger.info(f"Found {len(objects)} objects with prefix: {list_prefix}")
        
        return objects
    
    except S3Error as e:
        logger.error(f"Error listing files: {e}")
        return []

def remove_file(object_key, user_id=None):
    """
    Remove a file from MinIO, optionally checking user ownership.
    
    Args:
        object_key: The object key in MinIO
        user_id: ID of user requesting deletion (for authorization)
        
    Returns:
        bool: Success or failure
    """
    try:
        # If user_id is provided, verify ownership
        if user_id is not None:
            user_prefix = get_user_file_prefix(user_id)
            
            # Check if the object belongs to this user
            if not object_key.startswith(user_prefix):
                logger.warning(f"Access denied: {object_key} doesn't belong to user {user_id}")
                return False
        
        # Remove the object
        minio_client.remove_object(BUCKET_NAME, object_key)
        logger.info(f"File removed: {object_key}")
        return True
    
    except S3Error as e:
        logger.error(f"Error removing file: {e}")
        return False

def create_folder(folder_name, user_id, parent_folder=None):
    """
    Create a folder within a user's storage.
    
    Args:
        folder_name: Name of folder to create
        user_id: User ID who owns the folder
        parent_folder: Optional parent folder path
        
    Returns:
        str: The created folder's object key
    """
    try:
        user_prefix = get_user_file_prefix(user_id)
        
        # Build folder path
        if parent_folder:
            parent_folder = parent_folder.strip('/')
            folder_path = f"{user_prefix}{parent_folder}/{folder_name}"
        else:
            folder_path = f"{user_prefix}{folder_name}"
        
        # Ensure the path ends with a slash to denote a directory
        if not folder_path.endswith('/'):
            folder_path = folder_path + '/'
        
        # Create folder marker
        folder_marker = f"{folder_path}.folder"
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=folder_marker,
            data=BytesIO(b""),
            length=0,
            content_type="application/octet-stream",
            metadata={
                "folder_name": folder_name,
                "content_type": "application/directory"
            }
        )
        
        logger.info(f"Folder created: {folder_path}")
        return folder_path
    
    except S3Error as e:
        logger.error(f"Error creating folder: {e}")
        raise e