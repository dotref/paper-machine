from pydantic import BaseModel
from typing import List

class RAGResponse(BaseModel):
    response: str
    sources: List[dict]