from fastapi import Depends, HTTPException, status
import glob
import logging
import os
from typing import Any, Dict, List, Tuple
from huggingface_hub import snapshot_download
from minio import Minio
from minio.error import S3Error
import psycopg2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from .config import MODEL_CACHE_DIR, MODELS_BUCKET, BATCH_SIZE, CHUNK_SIZE, CHUNK_OVERLAP, DIMENSION

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


def save_embeddings_to_vectordb(
    pgvector_client: Any, 
    chunks: List[str], 
    embeddings: List[List[float]]
) -> None:
    '''
    This function will write an embeeding along with the embeddings text
    to the vector db.
    '''
    try:
        cursor = pgvector_client.cursor()
    
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting", error)

    try:
        for text, embedding in zip(chunks, embeddings):
            cursor.execute(
                "INSERT INTO embeddings (embedding, text) VALUES (%s, %s)",
                (embedding, text)
            )
        pgvector_client.commit()
    except (Exception, psycopg2.Error) as error:
        print("Error while writing to DB", error)
    finally:
        if cursor:
            cursor.close()

async def process_document_embeddings(
    minio_client: Minio,
    pgvector_client: Any,
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
        save_embeddings_to_vectordb(pgvector_client, chunks, embeddings)
        
        logger.info(f"Successfully processed embeddings for {object_key}")
        
    except Exception as e:
        logger.error(f"Error processing embeddings for {object_key}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing embeddings for {object_key}: {str(e)}"
        )