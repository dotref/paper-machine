from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
import os

from .routes.storage_router import router as storage_router
from .routes.auth_router import router as auth_router
from .routes.rag_router import router as rag_router

from .database.config import get_postgres_settings, get_embedding_model_settings
from .database.dependencies import get_db
from .database.utils import ensure_model_is_ready

from .minio.config import get_minio_settings
from .minio.dependencies import get_minio_client
from .minio.utils import initialize_minio

# Setup logging - Update to more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    try:
        # Validate settings
        get_minio_settings()
        get_postgres_settings()
        logger.info("Settings validated")

        # Initialize clients
        minio_client = get_minio_client()  # should be cached
        
        app.state.embed_on = os.environ.get('EMBED_ON', 'false').lower() == 'true'
        if app.state.embed_on:
            logger.info("Embedding on")
            # Ensure model is ready
            model_settings = get_embedding_model_settings()
            logger.info(f"Preparing model {model_settings['model']} revision {model_settings['revision']}")
            model_path = ensure_model_is_ready(minio_client, model_settings['model'], model_settings['revision'])
            
            # Set global model path
            app.state.model_path = model_path
            logger.info(f"Model ready at {model_path}")

        # Connect to database
        db = get_db()
        await db.connect()
        logger.info("Database connected")
        
        # Initialize MinIO storage
        initialize_minio()
        logger.info("MinIO initialized")

        yield
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    finally:
        # Close database connection
        if 'db' in locals():
            await db.disconnect()
        logger.info("Database disconnected")
        
        # Cleanup
        if 'pg_client' in locals():
            pg_client.close()
        logger.info("Shutting down")

# Create FastAPI app
app = FastAPI(
    title="Paper Machine API",
    description="API for managing document storage and processing",
    version="1.0.0",
    lifespan=lifespan,
) 

# Enable CORS - Update to include Authorization header
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],  # Explicitly include Authorization
)

# Include routers
app.include_router(storage_router)  # Use the consolidated storage router
app.include_router(auth_router)     # Authentication router
app.include_router(rag_router)      # RAG router

# Index Route
@app.get("/")
async def index():
    """Welcome endpoint"""
    logger.info("Index page accessed")
    return {
        "message": "Welcome to the Paper Machine API",
        "docs": "/docs",
        "auth_endpoints": "/auth",
        "storage_endpoints": "/storage"
    }

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=5000, reload=True)