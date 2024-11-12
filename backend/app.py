from datetime import datetime
from flask import Flask, request, jsonify
from typing import Dict, Any
import asyncio
from pathlib import Path
from flask_cors import CORS


# Import configurations
from config import config

# Import utilities
from utils import setup_logging, get_logger, timer

# Import data loader
from data_loader.parsers.parsers import PDFParser, TextParser, ImageParser

# Setup logging
setup_logging(log_level="DEBUG", log_file="app.log")
logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS

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
            "fields": "To be added"
        }
    })

# Main Routes
@app.route("/", methods=["GET"])
def index() -> Dict[str, str]:
    logger.info("Index page accessed")
    return jsonify({
        "message": "Welcome to the backend API",
        "available_endpoints": [
            "/health",
            "/upload",
            "/query"
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
    query = data.get('query', '')
    
    # TODO: add query processing logics here
    
    response = {
        "message": f"Received your message: {query}",
        "status": "processed",
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    return jsonify(response)

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(debug=True, host="0.0.0.0", port=3000)
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

"""