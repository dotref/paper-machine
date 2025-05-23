from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Annotated, List
import logging

from ..rag.utils import create_rag_response

from databases import Database
from ..database.dependencies import get_db
from ..auth.utils import get_current_user
from ..rag.dependencies import validate_object_keys
from ..rag.models import RAGResponse
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str
    object_keys: List[str]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/chat")
async def chat(
    payload: ChatRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
    request: Request
) -> RAGResponse:
    """
    Endpoint for RAG chatbot
    """
    query = payload.query
    object_keys = payload.object_keys

    response_text, sources = await create_rag_response(
        db=db,
        query=query,
        object_keys=object_keys,
        model_path=request.app.state.model_path
    )

    logger.info(f"Returning response to frontend: {response_text[:100]}...")
    return RAGResponse(
        response=response_text,
        sources=sources
    )
    