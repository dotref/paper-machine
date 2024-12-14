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
from agents.agentic_rag import MultiDocumentRetrieval, AgentChat
from utils import setup_logging, get_logger, timer
from data_loader.parsers.parsers import PDFParser, TextParser, ImageParser
from werkzeug.utils import secure_filename

# Add configurations
UPLOAD_FOLDER = 'backend/uploads'
PERSIST_DIR = 'backend/storage'
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

# Create uploads directory if it doesn't exist
os.makedirs(os.path.join(root_dir, UPLOAD_FOLDER), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Token Validation Setup
VALID_TOKENS = {"sample-token-123", "another-token-456"}  # Replace with secure tokens

def validate_token(token: str) -> bool:
    """
    Validate the provided token.
    """
    logger.debug(f"Received token: {token}")
    if not token:
        return False
    token = token.replace("Bearer ", "").strip()  # Remove "Bearer " prefix
    return token in VALID_TOKENS

def token_required(func):
    """
    Decorator to enforce token validation on routes.
    """
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if not validate_token(token):
            return jsonify({"error": "Invalid or missing token. Please provide a valid API token."}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Setup logging
setup_logging(log_level="DEBUG", log_file="app.log")
logger = get_logger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(root_dir, UPLOAD_FOLDER)
app.config['PERSIST_DIR'] = os.path.join(root_dir, PERSIST_DIR)

CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",  # Frontend dev port
            "http://127.0.0.1:3000"
        ]
    }
})

# Initialize knowledge base and parsers
knowledge_base = MultiDocumentRetrieval(app.config['UPLOAD_FOLDER'], app.config['PERSIST_DIR'])
knowledge_base.setup_indicies()
knowledge_base.setup_retriever()
atexit.register(knowledge_base.shutdown)

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
    """
    Health check endpoint for validating the token.
    """
    token = request.headers.get("Authorization", "")
    if not validate_token(token):
        return jsonify({"error": "Invalid or missing token."}), 401
    logger.info("Health check successful")
    return jsonify({"status": "healthy", "message": "Token is valid."})

# Main Routes
@app.route("/", methods=["GET"])
def index() -> Dict[str, str]:
    logger.info("Index page accessed")
    return jsonify({
        "message": "Welcome to the backend API",
        "available_endpoints": ["/health", "/upload", "/chat"]
    })

# Document Upload
@app.route("/upload", methods=["POST"])
@token_required
@timer
def upload_document():
    logger.info("Upload endpoint triggered")
    if 'file' not in request.files:
        return jsonify({"message": "No file provided", "status": "error"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No filename provided", "status": "error"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(file_path)
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in parsers:
                logger.info(f"File saved successfully: {filename}")
                knowledge_base.create_indices()
                knowledge_base.setup_retriever()
                return jsonify({
                    "message": f"File uploaded successfully",
                    "filename": filename,
                    "status": "processed",
                    "file_type": file_ext[1:].upper()
                })
            else:
                os.remove(file_path)
                return jsonify({"message": "Unsupported file type", "status": "error"}), 400
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return jsonify({"message": "Error saving file", "status": "error", "error": str(e)}), 500
    return jsonify({"message": "Invalid file type", "status": "error"}), 400

# Chat Endpoint
chat_sessions = {}

@app.route("/chat", methods=["POST"])
@token_required
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    session_id = request.headers.get('X-Session-ID', 'default')
    if session_id not in chat_sessions:
        chat_sessions[session_id] = AgentChat(knowledge_base)

    agent_chat = chat_sessions[session_id]
    message_queue = queue.Queue()
    agent_chat.set_message_queue(message_queue)

    def generate_stream():
        def process_message():
            asyncio.run(agent_chat.process_message(data['message']))
            message_queue.put(None)

        threading.Thread(target=process_message).start()
        timestamp = datetime.now().isoformat()
        while True:
            try:
                msg = message_queue.get()
                if msg is None:
                    break
                yield json.dumps({
                    "sender": msg["sender"],
                    "message": msg["content"],
                    "timestamp": timestamp,
                    "is_continuation": False,
                    "sources": msg.get("sources", [])
                }) + "\n\n"
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

@app.route("/uploads/<filename>")
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.teardown_appcontext
def shutdown_session(exception=None):
    knowledge_base.shutdown()

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(debug=True, host="0.0.0.0", port=5001)