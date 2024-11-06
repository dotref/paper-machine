# Project Architecture

This document outlines the architecture of the Multimodal Information Retrieval System.

## Project Structure

```
backend/
├── app.py                 # Main entry point - Flask application
├── config/
│   ├── __init__.py
│   └── settings.py       # Configuration settings (dev/prod/test)
├── agents/
│   ├── __init__.py
│   ├── base_agent.py     # Abstract base class for agents
│   ├── xxx_agent.py      # functionality implementation
├── models/
│   ├── __init__.py
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── embedding_model.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retriever.py
│   │   └── generator.py
│   └── schemas/          # Data models/schemas
│       ├── __init__.py
│       └── data_models.py
├── data_loader/
│   ├── __init__.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py
│   │   ├── text_parser.py
│   │   └── image_parser.py
│   └── database/
│       ├── __init__.py
│       └── db_handler.py
├── utils/
│   ├── __init__.py
│   └── helpers.py        # Common utility functions
└── requirements.txt    # Project dependencies
```

## Component Responsibilities

### Entry Point (`app.py`)
- Flask application setup
- API route definitions
- Middleware configuration
- Error handlers

### Config
- Environment-specific settings
- API keys and sensitive configurations
- Database configurations

### Agents
- `base_agent.py`: Abstract class defining common agent interfaces
- `xxx_agent.py`: Child class defining the specific actions

### Models
- `embeddings/`: Text and image embedding models
- `rag/`: Retrieval and generation components
- `schemas/`: Data models and validation

### Data Loader
- `parsers/`: Different file format parsers (PDF, text, images)
- `database/`: Database interaction layer

### Utils
- Helper functions
- Common utilities used across modules

## Design Principles
1. **Modularity**: Each component is designed to be independent and easily replaceable
2. **Extensibility**: New parsers, models, or agents can be added without modifying existing code
3. **Testability**: Clear separation of concerns makes testing easier
4. **Configuration**: Environment-specific settings are separated from code

## Development Guidelines
1. Follow PEP 8 style guide for Python code
2. Write tests for new functionality
3. Document public APIs and significant changes
4. Use type hints for better code maintainability