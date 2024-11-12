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
├── data_loader/
│   ├── __init__.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── parsers.py
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

### Data Loader
- `parsers/`: Different file format parsers (PDF, text, images)
- `database/`: Database interaction layer

### Utils
- Helper functions
- Common utilities used across modules