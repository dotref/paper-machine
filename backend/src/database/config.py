import os
import logging
import tempfile

logger = logging.getLogger(__name__)

# Model cache settings
MODEL_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'hf-models')
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

# Embedding settings
EMBED_ON = False
EMBEDDING_MODEL = 'intfloat/multilingual-e5-small'
EMBEDDING_MODEL_REVISION = 'ffdcc22a9a5c973ef0470385cef91e1ecb461d9f'
BATCH_SIZE = 1
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 10
DIMENSION = 384

# MinIO settings
MODELS_BUCKET = 'hf-models'
CUSTOM_CORPUS_BUCKET = 'custom-corpus'

MODEL_PATH = None  # Will be set during startup

VALID_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/json"
    # TODO: add more supported content types as needed
}

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
        'custom_corpus_bucket': CUSTOM_CORPUS_BUCKET
    }

def get_postgres_settings():
    """
    Get PostgreSQL settings from environment variables
    """
    if not os.environ.get('POSTGRES_USER') or not os.environ.get('POSTGRES_PASSWORD'):
        raise ValueError("PostgreSQL credentials not found in environment variables")
    
    return {
        'host': os.environ['POSTGRES_HOST'],
        'database': os.environ['POSTGRES_DB'],
        'user': os.environ['POSTGRES_USER'],
        'password': os.environ['POSTGRES_PASSWORD'],
        'port': os.environ['POSTGRES_PORT']
    }