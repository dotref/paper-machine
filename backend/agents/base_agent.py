from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class AgentResponse:
    """Standard response format for all agents"""
    success: bool
    data: Any
    message: str
    metadata: Optional[Dict[str, Any]] = None

class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._initialize()
    
    @abstractmethod
    def _initialize(self) -> None:
        """Initialize agent-specific components"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process input data and return response"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data format"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of agent capabilities"""
        pass