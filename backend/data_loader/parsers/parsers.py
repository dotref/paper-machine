from . import BaseParser
from typing import Any, Dict, List, BinaryIO

class PDFParser(BaseParser):
    def parse(self, file: BinaryIO) -> Dict[str, Any]:
        # TODO: Implement PDF parsing logic
        print(f"Parsing PDF file: {file.name}")
        return {"status": "PDF parsing not implemented"}
    
    def validate(self, file: BinaryIO) -> bool:
        # TODO: Implement PDF validation
        return file.name.lower().endswith('.pdf')
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.pdf']

class TextParser(BaseParser):
    def parse(self, file: BinaryIO) -> Dict[str, Any]:
        # TODO: Implement text parsing logic
        print(f"Parsing text file: {file.name}")
        return {"status": "Text parsing not implemented"}
    
    def validate(self, file: BinaryIO) -> bool:
        # TODO: Implement text validation
        return file.name.lower().endswith(('.txt', '.md'))
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.txt', '.md']

class ImageParser(BaseParser):
    def parse(self, file: BinaryIO) -> Dict[str, Any]:
        # TODO: Implement image parsing logic
        print(f"Parsing image file: {file.name}")
        return {"status": "Image parsing not implemented"}
    
    def validate(self, file: BinaryIO) -> bool:
        # TODO: Implement image validation
        return file.name.lower().endswith(('.jpg', '.jpeg', '.png'))
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.jpg', '.jpeg', '.png']