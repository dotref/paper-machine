from fastapi import Depends, HTTPException, status, UploadFile, Form, File
import psycopg2
from functools import lru_cache
import logging
from typing import Any
from pydantic import BaseModel
from databases import Database
from .config import get_postgres_settings

logger = logging.getLogger(__name__)

@lru_cache
def get_pg_client() -> Any:
    """
    Creates and returns a Postgres client instance.
    Cached to avoid creating multiple instances.
    """

    try:
        settings = get_postgres_settings()
        connection = psycopg2.connect(
            host=settings['host'], 
            database=settings['database'], 
            user=settings['user'], 
            password=settings['password'], 
            port=settings['port']
        )

        return connection
    except KeyError as e:
        logger.error(f"Missing environment variable: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Postgres configuration error: missing {e}"
        )
    except psycopg2.Error as e:
        logger.error(f"Postgres error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Postgres error: {str(e)}"
        )

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
