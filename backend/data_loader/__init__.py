from typing import BinaryIO, Dict, Any, Type
from .parsers.parsers import PDFParser, TextParser, ImageParser
from .database.db_handler import DatabaseHandler, MockDatabaseHandler

class DataLoader:
    def __init__(self, db_handler: Type[DatabaseHandler] = MockDatabaseHandler):
        self.parsers = {
            'pdf': PDFParser(),
            'text': TextParser(),
            'image': ImageParser()
        }
        self.db_handler = db_handler()
        self.db_handler.connect()
    
    def load_file(self, file: BinaryIO) -> Dict[str, Any]:
        """Load and parse a file, then store it in the database"""
        # Find appropriate parser
        extension = file.name.split('.')[-1].lower()
        parser = None
        
        for p in self.parsers.values():
            if f'.{extension}' in p.supported_extensions:
                parser = p
                break
        
        if not parser:
            raise ValueError(f"Unsupported file type: {extension}")
        
        # Parse and store
        parsed_data = parser.parse(file)
        doc_id = self.db_handler.store_document(parsed_data)
        
        return {
            "doc_id": doc_id,
            "status": "success",
            "parser_used": parser.__class__.__name__
        }
    
    def close(self):
        """Clean up resources"""
        self.db_handler.disconnect()

# Usage example:
"""
loader = DataLoader()
with open('example.pdf', 'rb') as file:
    result = loader.load_file(file)
print(result)
loader.close()
"""