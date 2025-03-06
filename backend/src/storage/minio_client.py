import os
from minio import Minio
from minio.error import S3Error
from io import BytesIO

# MinIO configuration
MINIO_URL = os.environ.get("MINIO_URL", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minio_user")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minio_password")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
BUCKET_NAME = "paper-machine"

# Initialize MinIO client
minio_client = Minio(
    endpoint=MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

def initialize_minio():
    """Initialize MinIO with default bucket if it doesn't exist."""
    try:
        if not minio_client.bucket_exists(BUCKET_NAME):
            minio_client.make_bucket(BUCKET_NAME)
            print(f"Created bucket: {BUCKET_NAME}")
    except S3Error as e:
        print(f"Error initializing MinIO: {e}")
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
        print(f"User storage area created: {user_id_prefix}")
        return True
    except S3Error as e:
        print(f"Error creating user storage area: {e}")
        return False

def get_user_file_prefix(user_id):
    """Get the proper prefix for user files."""
    return f"user-{user_id}/"

# Helper functions for storage operations
# ...existing code...