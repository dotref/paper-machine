from fastapi import Depends, HTTPException, status
import glob
import logging
import os
from typing import Any, Dict, List, Tuple
from huggingface_hub import snapshot_download
from minio import Minio
from minio.error import S3Error
from databases import Database
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from .config import BATCH_SIZE, CHUNK_SIZE, CHUNK_OVERLAP, DIMENSION
from ..minio.config import  MODEL_CACHE_DIR, MODELS_BUCKET

logger = logging.getLogger(__name__)

def upload_model_to_minio(
    minio_client: Minio, 
    bucket_name: str, 
    full_model_name: str, 
    revision: str
) -> None:
    '''
    Download a model from Hugging Face and upload it to MinIO. This function will use
    the current systems temp directory to temporarily save the model. 
    '''
    # Get the user name and the model name.
    tmp = full_model_name.split('/') 
    user_name = tmp[0]
    model_name = tmp[1]

    # The snapshot_download will use this pattern for the path name.
    model_path_name=f'models--{user_name}--{model_name}' 
    # The full path on the local drive. 
    full_model_local_path = os.path.join(MODEL_CACHE_DIR, model_path_name, 'snapshots', revision)
    # The path used by MinIO. 
    full_model_object_path = model_path_name + '/snapshots/' + revision

    print(f'Starting download from HF to {full_model_local_path}.')
    snapshot_download(repo_id=full_model_name, revision=revision, cache_dir=MODEL_CACHE_DIR)

    print('Uploading to MinIO.')
    upload_local_directory_to_minio(minio_client, full_model_local_path, bucket_name, full_model_object_path)


def upload_local_directory_to_minio(
    minio_client: Minio, 
    local_path:str, 
    bucket_name:str , 
    minio_path:str
) -> None:
    assert os.path.isdir(local_path)

    for local_file in glob.glob(local_path + '/**'):
        local_file = local_file.replace(os.sep, '/') # Replace \ with / on Windows
        if not os.path.isfile(local_file):
            upload_local_directory_to_minio(minio_client, local_file, bucket_name, minio_path + '/' + os.path.basename(local_file))
        else:
            remote_path = os.path.join(minio_path, local_file[1 + len(local_path):])
            remote_path = remote_path.replace(os.sep, '/')  # Replace \ with / on Windows
            minio_client.fput_object(bucket_name, remote_path, local_file)


def download_model_from_minio(minio_client: Minio, bucket_name: str, full_model_name: str, revision: str) -> str:
    # Get the user name and the model name.
    tmp = full_model_name.split('/') 
    user_name = tmp[0]
    model_name = tmp[1]

    # The snapshot_download will use this pattern for the path name.
    model_path_name = f'models--{user_name}--{model_name}' 
    # The full path on the local drive. 
    full_model_local_path = os.path.join(MODEL_CACHE_DIR, model_path_name, 'snapshots', revision)
    # The path used by MinIO. 
    full_model_object_path = model_path_name + '/snapshots/' + revision 

    # Create the local directory if it doesn't exist
    os.makedirs(full_model_local_path, exist_ok=True)

    # Download from MinIO
    for obj in minio_client.list_objects(bucket_name, prefix=full_model_object_path, recursive=True):
        file_path = os.path.join(MODEL_CACHE_DIR, obj.object_name)
        # Ensure the parent directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        minio_client.fget_object(bucket_name, obj.object_name, file_path)
    
    return full_model_local_path


def ensure_model_is_ready(
    minio_client: Minio,
    full_model_name: str,
    revision: str = "latest"
) -> str:
    '''
    Ensures model is available locally, downloading from Hugging Face and caching in MinIO if needed.
    Returns the local path to the model.
    '''
    try:
        # Get the user name and the model name
        user_name, model_name = full_model_name.split('/')
        model_path_name = f'models--{user_name}--{model_name}'
        full_model_local_path = os.path.join(MODEL_CACHE_DIR, model_path_name, 'snapshots', revision)
        
        # If model exists locally and directory is not empty, use it
        if os.path.exists(full_model_local_path) and any(os.scandir(full_model_local_path)):
            logger.info(f"Using locally cached model at {full_model_local_path}")
            return full_model_local_path
            
        # Check MinIO
        full_model_object_path = f"{model_path_name}/snapshots/{revision}"
        objects = minio_client.list_objects(MODELS_BUCKET, prefix=full_model_object_path, recursive=True)
        if len(list(objects)) > 0:
            logger.info(f"Model {full_model_name} exists in MinIO, downloading to local cache")
            return download_model_from_minio(minio_client, full_model_name, revision, full_model_local_path)
            
        # Not in MinIO or local, download from Hugging Face and cache in MinIO
        logger.info(f"Downloading model {full_model_name} from Hugging Face")
        upload_model_to_minio(minio_client, MODELS_BUCKET, full_model_name, revision)
        
        return full_model_local_path
        
    except Exception as e:
        logger.error(f"Error ensuring model is ready: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare model: {str(e)}"
        )


def create_embeddings(
    model_path: str, 
    text: str, 
    chunk_size: int = CHUNK_SIZE, 
    chunk_overlap: int = CHUNK_OVERLAP
) -> Tuple[List[str], List[List[float]]]:
    '''
    This function will create embeddings for a given file using a model.
    Returns a tuple of (chunks, embeddings)
    '''
    # Load the model
    model = SentenceTransformer(model_path)
    
    # Create text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    # Split text into chunks
    chunks = text_splitter.split_text(text)
    
    # Generate embeddings
    embeddings = model.encode(chunks, batch_size=BATCH_SIZE).tolist()
    
    logger.info(f"Created {len(chunks)} embeddings")
    return chunks, embeddings


async def save_embeddings_to_vectordb(
    db: Database, 
    object_key: str,
    chunks: List[str], 
    embeddings: List[List[float]]
) -> None:
    '''
    This function will write embeddings along with their text
    to the vector db using the Database object from databases package.
    '''
    try:
        # Prepare the query for bulk insert
        query = """
        INSERT INTO embeddings (object_key, embedding, text)
        VALUES (:object_key, :embedding, :text)
        """
        values = [{"object_key": object_key, "embedding": embedding, "text": text} for text, embedding in zip(chunks, embeddings)]
        
        # Execute the bulk insert
        await db.execute_many(query=query, values=values)
        
        logger.info(f"Successfully saved {len(chunks)} embeddings to vector database")
    except Exception as error:
        logger.error(f"Error while writing to DB: {error}")
        raise


async def process_document_embeddings(
    minio_client: Minio,
    db: Database,
    bucket_name: str,
    object_key: str,
    model_path: str,
) -> None:
    '''
    Background task to process document embeddings:
    1. Stream document from MinIO
    2. Create embeddings in chunks
    3. Save embeddings to vector database
    '''
    try:
        logger.info(f"Starting embedding creation for document {object_key}")
        
        # Get document content from MinIO
        data = minio_client.get_object(bucket_name, object_key)
        
        text = data.read().decode('utf-8')
        
        # Create embeddings
        chunks, embeddings = create_embeddings(model_path, text)
        
        # Save to vector database
        await save_embeddings_to_vectordb(db, object_key, chunks, embeddings)
        
        logger.info(f"Successfully processed embeddings for {object_key}")
        
    except Exception as e:
        logger.error(f"Error processing embeddings for {object_key}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing embeddings for {object_key}: {str(e)}"
        )

async def search_similar_chunks_by_objects(
    db: Database,
    query_embedding: List[float],
    object_keys: List[str],
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Perform semantic search on embeddings, but only for specific object_keys.
    Returns chunks sorted by similarity, along with their source object_key.
    
    Args:
        db: Database connection
        query_embedding: The query vector to compare against
        object_keys: List of object_keys to search within
        limit: Maximum number of results to return
        similarity_threshold: Minimum similarity score (0 to 1) to include in results
    
    Returns:
        List of dicts containing text, similarity score, and object_key
    """
    try:
        query = """
        SELECT 
            text,
            object_key,
            1 - (embedding <=> :query_embedding) as similarity
        FROM embeddings
        WHERE 
            object_key = ANY(:object_keys)
            AND 1 - (embedding <=> :query_embedding) > :threshold
        ORDER BY similarity DESC
        LIMIT :limit
        """
        values = {
            "query_embedding": query_embedding,
            "object_keys": object_keys,
            "threshold": similarity_threshold,
            "limit": limit
        }
        
        results = await db.fetch_all(query, values)
        
        return [
            {
                "text": row['text'],
                "object_key": row['object_key'],
                "similarity": float(row['similarity'])
            }
            for row in results
        ]
        
    except Exception as error:
        logger.error(f"Error performing semantic search: {error}")
        raise