import os
from databases import Database

# Get PostgreSQL connection details from environment variables
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "pgvector")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "vectordb")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "testuser")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "testpwd")

# Construct database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create a database instance
database = Database(DATABASE_URL)

async def get_db():
    """
    Get a database connection for dependency injection.
    """
    return database
