from datetime import datetime
from flask import Flask, request, jsonify
from typing import Dict, Any
import asyncio
from pathlib import Path
from flask_cors import CORS
import os

# Import configurations
from agents.agentic_rag import MultiDocumentRAG
from config import config

# Import utilities
from utils import setup_logging, get_logger, timer

# Import data loader
from data_loader.parsers.parsers import PDFParser, TextParser, ImageParser

from werkzeug.utils import secure_filename

# Add these configurations after creating the Flask app
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Setup logging
setup_logging(log_level="DEBUG", log_file="app.log")
logger = get_logger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",  # Next.js default dev port
            "http://127.0.0.1:3000"
        ]
    }
})

rag = MultiDocumentRAG()


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
        return jsonify({
            "message": "No file provided",
            "status": "error"
        }), 400
        
    file = request.files['file']
    if file.filename == '':
        logger.info("No selected file")
        return jsonify({
            "message": "No filename provided",
            "status": "error"
        }), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            # Save the file
            file.save(file_path)
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Process the file based on its type
            if file_ext in parsers:
                # Here you would actually process the file with your parser
                # For now, we'll just acknowledge receipt
                logger.info(f"File saved successfully: {filename}")
                cleaned_filename = ''.join(char for char in filename if char.isalnum() or char in '_-')
                rag.add_document(file_path, cleaned_filename)
                return jsonify({
                    "message": f"File uploaded successfully",
                    "filename": filename,
                    "status": "processed",
                    "file_type": file_ext[1:].upper()  # Remove the dot and capitalize
                })
            else:
                os.remove(file_path)  # Remove unsupported file
                return jsonify({
                    "message": "Unsupported file type",
                    "status": "error"
                }), 400
                
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return jsonify({
                "message": "Error saving file",
                "status": "error",
                "error": str(e)
            }), 500
    
    return jsonify({
        "message": "Invalid file type",
        "status": "error"
    }), 400


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
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        query = data.get('query', '')
        if not query:
            return jsonify({"error": "No query provided"}), 400
            
        # Log the received query
        logger.info(f"Received query: {query}")
        
        # TODO: Add actual query logic using rag here
        rag.setup_agent() # TODO: DO NOT USE THIS FUNCTION
        # USE llama-index insert_node when upload document, load everything instead of re-init
        # process query
        response, sources = rag.query(query)

        # Format sources information as a string
        sources_text = ""
        for idx, source in enumerate(sources, 1):
            sources_text += f"\nSource {idx}:\n"
            sources_text += f"Document: {source['metadata']['document_name']}\n"
            sources_text += f"Text: {source['text'][:200]}...\n"
            if source["score"] is not None:
                sources_text += f"Score: {source['score']:.4f}\n"
            if 'page_label' in source['metadata']:
                sources_text += f"Page: {source['metadata']['page_label']}\n"

        # Construct the message that matches frontend format
        json_response = {
            "message": f"Query: {query}\nResponse: {response}\n\nSources:{sources_text}",
            "status": "processed",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Sending response: {json_response}")
        return jsonify(json_response)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

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

"""