from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
from .database.router import router as storage_router
from .database.config import get_minio_settings, get_postgres_settings

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up")
    # Validate environment variables on startup
    try:
        minio_settings = get_minio_settings()
        postgres_settings = get_postgres_settings()
        logger.info("Successfully loaded MinIO and PostgreSQL configurations")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    yield

    logger.info("Shutting down")

# Create FastAPI app
app = FastAPI(
    title="Paper Machine API",
    description="API for managing document storage and processing",
    version="1.0.0",
    lifespan=lifespan
) 

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(storage_router)

# Index Route
@app.get("/")
async def index():
    """Welcome endpoint"""
    logger.info("Index page accessed")
    return {
        "message": "Welcome to the Paper Machine API",
        "docs": "/docs",
        "storage_endpoints": "/storage"
    }

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=5000, reload=True)