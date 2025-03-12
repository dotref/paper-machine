import os

# Embedding settings
BATCH_SIZE = 1
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 10
DIMENSION = 384

VALID_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/json"
    # TODO: add more supported content types as needed
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

def get_embedding_model_settings():
    """
    Get embedding model settings from environment variables
    """
    if not os.environ.get('EMBEDDING_MODEL') or not os.environ.get('EMBEDDING_MODEL_REVISION'):
        raise ValueError("Embedding model credentials not found in environment variables")
    
    return {
        'model': os.environ['EMBEDDING_MODEL'],
        'revision': os.environ['EMBEDDING_MODEL_REVISION']
    }