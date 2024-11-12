from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Document:
    """Represents a document in the system"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: datetime = datetime.now()

@dataclass
class QueryResult:
    """Represents a query result"""
    query: str
    documents: List[Document]
    generated_response: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class ModelConfig:
    """Configuration for various models"""
    model_name: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any] = None