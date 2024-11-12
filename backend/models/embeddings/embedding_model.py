from abc import ABC, abstractmethod
from typing import List, Union, Dict, Any
import numpy as np

class BaseEmbeddingModel(ABC):
    """Base class for all embedding models"""
    
    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Convert text to embedding vector"""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Convert batch of texts to embedding vectors"""
        pass
    
    @abstractmethod
    def embed_image(self, image_path: str) -> np.ndarray:
        """Convert image to embedding vector"""
        pass

class OpenAIEmbedding(BaseEmbeddingModel):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # TODO: Initialize OpenAI client
        pass
    
    def embed_text(self, text: str) -> np.ndarray:
        # TODO: Implement OpenAI text embedding
        pass
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        # TODO: Implement batch embedding
        pass
    
    def embed_image(self, image_path: str) -> np.ndarray:
        # TODO: Implement image embedding
        pass