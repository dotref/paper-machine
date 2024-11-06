from flask import Flask, request, jsonify
from typing import Dict, Any
import logging
"""
# Test the home page
curl http://localhost:5000/

# Test health check
curl http://localhost:5000/health

# Test upload endpoint
curl -X POST http://localhost:5000/upload -F "file=assets/test.txt" # consider changing to pdfs in your test

# Test search endpoint
curl -X POST http://localhost:5000/search -H "Content-Type: application/json" -d '{"query": "test search"}'

# Test query endpoint
curl -X POST http://localhost:5000/query -H "Content-Type: application/json" -d '{"query": "test query"}'

# Test models listing
curl http://localhost:5000/models

# Test specific model info
curl http://localhost:5000/models/model1
"""
# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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
def health_check() -> Dict[str, str]:
    logger.info("Health check requested")
    return jsonify({"status": "healthy"})

# Main Routes
@app.route("/", methods=["GET"])
def index() -> Dict[str, str]:
    logger.info("Index page accessed")
    return jsonify({
        "message": "Welcome to Paper Machine API"
    })

# Document Upload
@app.route("/upload", methods=["POST"])
def upload_document():
    logger.info("Document upload initiated")
    # Debug info about the upload request
    files = request.files
    logger.debug(f"Received files: {list(files.keys())}")
    
    return jsonify({
        "message": "Upload endpoint accessed",
        "files_received": len(files),
        "status": "upload handler not yet implemented"
    })

# Query Endpoint
@app.route("/query", methods=["POST"])
def process_query():
    logger.info("Query processing initiated")
    query_data = request.get_json()
    logger.debug(f"Received query: {query_data}")
    
    return jsonify({
        "message": "Query endpoint accessed",
        "query_received": query_data,
        "status": "query processor not yet implemented"
    })

# Search Endpoint
@app.route("/search", methods=["POST"])
def search():
    logger.info("Search initiated")
    search_params = request.get_json()
    logger.debug(f"Search parameters: {search_params}")
    
    return jsonify({
        "message": "Search endpoint accessed",
        "search_params": search_params,
        "status": "search function not yet implemented"
    })

# Model Management
@app.route("/models", methods=["GET"])
def list_models():
    logger.info("Model listing requested")
    return jsonify({
        "message": "Model listing endpoint accessed",
        "models": [],
        "status": "model listing not yet implemented"
    })

@app.route("/models/<model_id>", methods=["GET"])
def get_model_info(model_id: str):
    logger.info(f"Model info requested for model_id: {model_id}")
    return jsonify({
        "message": f"Model info endpoint accessed for model: {model_id}",
        "model_id": model_id,
        "status": "model info retrieval not yet implemented"
    })

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(debug=True, host="0.0.0.0", port=5000)