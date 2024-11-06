from abc import ABC, abstractmethod
from typing import Any, Dict, List, BinaryIO

class BaseParser(ABC):
    """Abstract base class for all parsers"""
    
    @abstractmethod
    def parse(self, file: BinaryIO) -> Dict[str, Any]:
        """Parse a file and return structured data"""
        pass
    
    @abstractmethod
    def validate(self, file: BinaryIO) -> bool:
        """Validate if the file can be parsed by this parser"""
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of supported file extensions"""
        pass