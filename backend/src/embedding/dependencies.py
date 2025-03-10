from fastapi import Depends, HTTPException, status, UploadFile, Form, File
from functools import lru_cache
import logging
from pydantic import BaseModel
from databases import Database
from .config import get_postgres_settings

logger = logging.getLogger(__name__)

@lru_cache
def get_db() -> Database:
    """
    Get a database connection for dependency injection.
    """
    try:
        settings = get_postgres_settings()
        database_url = f"postgresql://{settings['user']}:{settings['password']}@{settings['host']}:{settings['port']}/{settings['database']}"
        return Database(database_url)
    except KeyError as e:
        logger.error(f"Missing environment variable: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Postgres configuration error: missing {e}"
        )
