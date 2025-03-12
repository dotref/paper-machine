from fastapi import Depends, HTTPException
from typing import Annotated, List
from ..database.dependencies import get_db
from databases import Database

async def validate_object_keys(
    object_keys: List[str],
    db: Annotated[Database, Depends(get_db)] = None
) -> List[str]:
    """
    Validate that the user has access to the object keys, returns a subset
    of the object keys in case the user doesn't have access to all of them
    TODO: show error message to user in the case of access error
    """
    if not object_keys:
        return []
    try:
        query = """
        SELECT object_key
        FROM user_files
        WHERE object_key = ANY(:object_keys)
        """
        values = {"object_keys": object_keys}
        results = await db.fetch_all(query, values)
        return [row["object_key"] for row in results]
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Failed to check file existence")