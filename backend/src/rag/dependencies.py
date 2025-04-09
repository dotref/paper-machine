from fastapi import Depends, HTTPException
from typing import Annotated, List
from ..database.dependencies import get_db
from ..auth.utils import get_current_user
from databases import Database
import logging

logger = logging.getLogger(__name__)

async def validate_object_keys(
    object_keys: List[str],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)] = None
) -> List[str]:
    """
    Validate that the user has access to the object keys, returns a subset
    of the object keys in case the user doesn't have access to all of them
    TODO: show error message to user in the case of access error
    """
    username = current_user["username"]
    logger.info(f"Validating object keys for user {username}: {object_keys}")
    if not object_keys:
        return []
    try:
        query = """
        SELECT object_key
        FROM user_files
        WHERE object_key = ANY(:object_keys)
        AND username = :username
        """
        values = {"object_keys": object_keys, "username": username}
        results = await db.fetch_all(query, values)
        return [row["object_key"] for row in results]
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Failed to check file existence")