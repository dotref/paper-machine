import os
from typing import Dict, Any
from dataclasses import dataclass

from dotenv import load_dotenv

@dataclass
class OpenAIConfig:
    api_key: str
    model: str = "gpt-3.5-turbo-1106"  # default model, TODO use gpt-4 for better performance
    temperature: float = 0
    max_tokens: int = 2000

@dataclass
class DatabaseConfig:
    # TODO: Implement database configuration
    pass

@dataclass
class VectorStoreConfig:
    # TODO: Implement vector store configuration 
    pass

@dataclass
class ParserConfig:
    # TODO: Implement parser configurations for different file types
    pass

class Config:
    def __init__(self):
        load_dotenv()
        # Initialize OpenAI configuration
        self.openai = OpenAIConfig(
            api_key=os.getenv('OPENAI_API_KEY', ''),
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo-1106'),
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0')),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        )
        
        # TODO: Initialize other configurations
        self.database = DatabaseConfig()
        self.vector_store = VectorStoreConfig()
        self.parser = ParserConfig()

    def validate(self) -> bool:
        """Validate the configuration settings."""
        if not self.openai.api_key:
            raise ValueError("OpenAI API key is not set")
        return True

    @property
    def as_dict(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return {
            "openai": {
                "model": self.openai.model,
                "temperature": self.openai.temperature,
                "max_tokens": self.openai.max_tokens,
                # Not including API key for security
            }
            # TODO: Add other configurations as they are implemented
        }

# Create a global config instance
config = Config()