import os
import tempfile

VALID_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/json"
    # TODO: add more supported content types as needed
}

# Model cache settings
MODEL_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'hf-models')
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

MODELS_BUCKET = 'hf-models'
BUCKET_NAME = 'paper-machine'

def get_minio_settings():
    """
    Get MinIO settings from environment variables
    """
    if not os.environ.get('MINIO_ACCESS_KEY') or not os.environ.get('MINIO_SECRET_KEY') or not os.environ.get('MINIO_SECURE'):
        raise ValueError("MinIO credentials not found in environment variables")
    
    return {
        'url': os.environ['MINIO_URL'],
        'access_key': os.environ['MINIO_ACCESS_KEY'],
        'secret_key': os.environ['MINIO_SECRET_KEY'],
        'secure': os.environ['MINIO_SECURE'].lower() == 'true',
        'models_bucket': MODELS_BUCKET,
        'custom_corpus_bucket': BUCKET_NAME
    }