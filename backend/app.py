from datetime import datetime
from flask import Flask, request, jsonify, stream_with_context, Response, send_from_directory
from typing import Dict, Any
import asyncio
from pathlib import Path
from flask_cors import CORS
import os
import queue
import threading
import json
import atexit

import pyprojroot
root_dir = pyprojroot.here()

# Import configurations
# from agents.agentic_rag import MultiDocumentRAG
from agents.agentic_rag import MultiDocumentRetrieval, AgentChat
from config import config

# Import utilities
from utils import setup_logging, get_logger, timer

# Import data loader
from data_loader.parsers.parsers import PDFParser, TextParser, ImageParser

from werkzeug.utils import secure_filename

# Add these configurations after creating the Flask app
UPLOAD_FOLDER = 'backend/uploads'
PERSIST_DIR = 'backend/storage'
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

# Create uploads directory if it doesn't exist
os.makedirs(os.path.join(root_dir, UPLOAD_FOLDER), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Setup logging
setup_logging(log_level="DEBUG", log_file="app.log")
logger = get_logger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(root_dir, UPLOAD_FOLDER)  # Set the UPLOAD_FOLDER
app.config['PERSIST_DIR'] = os.path.join(root_dir, PERSIST_DIR)  # Set the PERSIST_DIR

CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",  # Next.js default dev port
            "http://127.0.0.1:3000"
        ]
    }
})

knowledge_base = MultiDocumentRetrieval(app.config['UPLOAD_FOLDER'], app.config['PERSIST_DIR'])
knowledge_base.setup_indicies()
knowledge_base.setup_retriever()
atexit.register(knowledge_base.shutdown)

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
        original_filename = file.filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            # Save the file
            file.save(file_path)
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Process the file based on its type
            if file_ext in parsers:
                # TODO: Add actual processing logic here + database
                logger.info(f"File saved successfully: {filename}")
                knowledge_base.create_indices()
                knowledge_base.setup_retriever()
                logger.info(f"Indices created successfully")

                return jsonify({
                    "message": f"File uploaded successfully",
                    "filename": original_filename,  # Return the original file name
                    "stored_filename": filename,  # Return the stored file name
                    "status": "processed",
                    "file_type": file_ext[1:].upper()  # Remove the dot and capitalize
                })
            else:
                logger.info(f"Unsupported file type: {file_ext}")
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

# Global chat sessions dictionary to store AgentChat instances
chat_sessions = {}

@app.route("/chat", methods=["POST"])
def chat():
    """
    Endpoint that processes messages through AgentChat and streams responses
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    session_id = request.headers.get('X-Session-ID', 'default')
    
    # Create new chat session if it doesn't exist
    if session_id not in chat_sessions:
        logger.info(f"Creating new chat session for ID: {session_id}")
        chat_sessions[session_id] = AgentChat(knowledge_base)
    else:
        logger.info(f"Using existing chat session for ID: {session_id}")
    
    agent_chat = chat_sessions[session_id]
    message_queue = queue.Queue()
    agent_chat.set_message_queue(message_queue)

    def generate_stream():
        # Start processing in a separate thread
        def process_message():
            asyncio.run(agent_chat.process_message(data['message']))
            # Add None to queue to signal completion
            message_queue.put(None)
            
        thread = threading.Thread(target=process_message)
        thread.start()
        
        timestamp = datetime.now().isoformat()
        
        while True:
            # TODO: Implement streaming, can view commented code at end of file for dummy streaming example
            try:
                msg = message_queue.get()
                if msg is None:  # End of processing
                    break
                    
                message_data = {
                    "sender": msg["sender"],
                    "message": msg["content"],
                    "timestamp": timestamp,
                    "is_continuation": False,
                    "sources": msg.get("sources", [])
                }
                
                yield json.dumps(message_data) + "\n\n"
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in stream generation: {e}")
                break

    return Response(
        stream_with_context(generate_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

# # Global message queue for each chat session
# chat_queues = {}

# @app.route("/chat", methods=["POST"])
# def chat():
#     """
#     Test endpoint that streams tokens one by one to build a sentence
#     """
#     def generate_test_stream():
#         import time
        
#         # The sentence we'll stream token by token
#         sentence = "Hello! This is a test message being streamed one word at a time."
#         tokens = sentence.split()
        
#         # Initialize the first message
#         message_data = {
#             "sender": "TestBot",
#             "message": tokens[0],
#             "timestamp": datetime.now().isoformat()
#         }
#         yield json.dumps(message_data) + "\n\n"  # Add extra newline for proper flushing
        
#         # Stream subsequent tokens as updates to the same message
#         for token in tokens[1:]:
#             time.sleep(1)  # Wait 1 second between tokens
#             message_data = {
#                 "sender": "TestBot",
#                 "message": token,
#                 "timestamp": message_data["timestamp"],  # Keep same timestamp for continuation
#                 "is_continuation": True  # Flag to indicate this is part of the same message
#             }
#             yield json.dumps(message_data) + "\n\n"  # Add extra newline for proper flushing

#     return Response(
#         stream_with_context(generate_test_stream()),
#         mimetype='text/event-stream',
#         headers={
#             'Cache-Control': 'no-cache',
#             'Connection': 'keep-alive',
#             'X-Accel-Buffering': 'no'  # Disable nginx buffering if using nginx
#         }
#     )


@app.teardown_appcontext
def shutdown_session(exception=None):
    logger.info("Shutting down Flask application...")
    knowledge_base.shutdown()

# Add this new route to serve files from the upload folder
@app.route("/uploads/<filename>")
def serve_file(filename):
    """Serve uploaded files."""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    logger.info(f"Request to serve file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return jsonify({"error": "File not found"}), 404
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


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