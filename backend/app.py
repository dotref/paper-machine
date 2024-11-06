from flask import Flask, request, jsonify
from typing import Dict, Any
import asyncio
from pathlib import Path

# Import configurations
from config import config

# Import utilities
from utils import setup_logging, get_logger, timer

# Import agents
from agents import get_agent, AgentResponse

# Import models
from models import (
    OpenAIEmbedding,
    VectorRetriever, 
    LLMGenerator,
    Document,
    QueryResult
)

# Import data loader
from data_loader.database import get_db_handler
from data_loader.parsers.parsers import PDFParser, TextParser, ImageParser

# Setup logging
setup_logging(log_level="DEBUG", log_file="app.log")
logger = get_logger(__name__)

app = Flask(__name__)


# Initialize components (with minimal implementations)
embedding_model = OpenAIEmbedding(config=config.openai.__dict__)
retriever = VectorRetriever(embedding_model=embedding_model)
generator = LLMGenerator(config=config.openai.__dict__)
db_handler = get_db_handler()

# Initialize parsers
parsers = {
    '.pdf': PDFParser(),
    '.txt': TextParser(),
    '.jpg': ImageParser(),
    '.png': ImageParser()
}

# Error Handlers
@app.errorhandler(404)
def not_found(error) -> Dict[str, Any]:
    logger.error(f"Not found error: {error}")
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_server_error(error) -> Dict[str, Any]:
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Health Check
@app.route("/health", methods=["GET"])
@timer
def health_check() -> Dict[str, str]:
    logger.info("Health check requested")
    return jsonify({
        "status": "healthy",
        "components": {
            "database": db_handler.connected,
            "embedding_model": bool(embedding_model),
            "retriever": bool(retriever),
            "generator": bool(generator)
        }
    })

# Main Routes
@app.route("/", methods=["GET"])
def index() -> Dict[str, str]:
    logger.info("Index page accessed")
    return jsonify({
        "message": "Welcome to the backend API, reach out to Tony if you need help, thanks!",
        "available_endpoints": [
            "/health",
            "/upload",
            "/query",
            "/search"
        ]
    })

# Document Upload
@app.route("/upload", methods=["POST"])
@timer
def upload_document():
    logger.info("Upload endpoint triggered")
    
    if 'file' not in request.files:
        logger.info("No file part in request")
        return jsonify({"message": "No file provided"}), 400
        
    file = request.files['file']
    if file.filename == '':
        logger.info("No selected file")
        return jsonify({"message": "No filename provided"}), 400

    # Log file information
    logger.info(f"File upload attempted - Filename: {file.filename}")
    
    return jsonify({
        "message": "File upload received",
        "filename": file.filename,
        "status": "processed"
    })


# Query Endpoint
@app.route("/query", methods=["POST"])
@timer
def process_query():
    """
    Query endpoint provides RAG-based answers:
    - Retrieves relevant context
    - Generates new response
    - Question answering focus
    
    Example request:
    {
        "query": "what are the key findings in recent ML papers?",
        "response_format": "detailed"
    }
    """
    logger.info("Query endpoint triggered")
    data = request.get_json()
    return jsonify({
        "message": "Query received",
        "query": data.get('query', ''),
        "status": "processed"
    })

# Search Endpoint
@app.route("/search", methods=["POST"])
@timer
def search():
    """
    Search endpoint focuses on document retrieval:
    - Returns relevant documents/passages
    - No generation/answering
    - Pure vector similarity search
    
    Example request:
    {
        "query": "machine learning papers",
        "limit": 5,
        "filters": {"year": 2023, "topic": "AI"}
    }
    """
    logger.info("Search endpoint triggered")
    data = request.get_json()
    return jsonify({
        "message": "Search received",
        "query": data.get('query', ''),
        "status": "processed"
    })

# Model Management
@app.route("/models", methods=["GET"])
@timer
def list_models():
    logger.info("Model listing requested")
    return jsonify({
        "models": {
            "embedding": embedding_model.__class__.__name__,
            "retriever": retriever.__class__.__name__,
            "generator": generator.__class__.__name__
        }
    })

@app.route("/models/<model_id>", methods=["GET"])
@timer
def get_model_info(model_id: str):
    logger.info(f"Model info requested for model_id: {model_id}")
    
    models = {
        "embedding": embedding_model,
        "retriever": retriever,
        "generator": generator
    }
    
    if model_id not in models:
        return jsonify({"error": "Model not found"}), 404
        
    return jsonify({
        "model_id": model_id,
        "type": models[model_id].__class__.__name__,
        "status": "active"
    })

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(debug=True, host="0.0.0.0", port=5000)
    """
    # Entry point - Get API info
    curl http://localhost:5000/

    # Health check
    curl http://localhost:5000/health

    # Upload a file (replace path/to/file.pdf with actual file path)
    curl -X POST http://localhost:5000/upload -F "file=@../assets/test.txt"

    # Process a query
    curl -X POST http://localhost:5000/query \
    -H "Content-Type: application/json" \
    -d '{ 
        "query": "What is machine learning?" 
    }'

    # Search documents
    curl -X POST http://localhost:5000/search \
    -H "Content-Type: application/json" \
    -d '{
        "query": "find documents about AI"
    }'

    # List available models
    curl http://localhost:5000/models

    # Get specific model info
    curl http://localhost:5000/models/embedding
"""