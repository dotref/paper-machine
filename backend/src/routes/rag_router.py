from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Annotated, List
import logging

from ..rag.utils import create_rag_response

from databases import Database
from ..database.dependencies import get_db
from ..auth.utils import get_current_user
from ..rag.dependencies import validate_object_keys

from .models import RAGResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/chat")
async def chat(
    query: str,
    object_keys: Annotated[List[str], Depends(validate_object_keys)],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
    request: Request
) -> RAGResponse:
    """
    Endpoint for RAG chatbot
    """
    logger.info(f"RAG chat request: {query} with source objects: {object_keys}")
    response, sources = await create_rag_response(
        db=db,
        query=query,
        object_keys=object_keys,
        model_path=request.app.state.model_path
    )
    logger.info(f"RAG response: {response}")
    return RAGResponse(
        response=response,
        sources=sources
    )
    