import logging
import json
import uuid
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import wraps
from datetime import datetime

# Logging Setup
def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Setup logging configuration
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        log_format: Optional custom log format
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    Args:
        name: Name for the logger
    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)

# Performance Monitoring
def timer(func):
    """
    Decorator to measure function execution time
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logging.debug(f"{func.__name__} took {end_time - start_time:.2f} seconds")
        return result
    return wrapper

# File Operations
def validate_file_type(file_path: str, allowed_extensions: List[str]) -> bool:
    """
    Validate if file has allowed extension
    Args:
        file_path: Path to the file
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.txt'])
    Returns:
        bool: True if file type is allowed
    """
    return Path(file_path).suffix.lower() in allowed_extensions

# JSON Helpers
def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load JSON file
    Args:
        file_path: Path to JSON file
    Returns:
        Dict containing JSON data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading JSON file {file_path}: {e}")
        raise

def save_json(data: Dict[str, Any], file_path: str, pretty: bool = True) -> None:
    """
    Save data to JSON file
    Args:
        data: Data to save
        file_path: Path to save JSON file
        pretty: Whether to format JSON with indentation
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving JSON file {file_path}: {e}")
        raise

# Error Handling
class RetryableError(Exception):
    """Error that can be retried"""
    pass

# this is used for openai to retry in case of down time or traffic spikes
def retry_operation(
    operation,
    max_attempts: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = True
) -> Any:
    """
    Retry an operation with exponential backoff
    Args:
        operation: Function to retry
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
    Returns:
        Result of the operation
    """
    for attempt in range(max_attempts):
        try:
            return operation()
        except RetryableError as e:
            if attempt == max_attempts - 1:
                raise
            wait_time = delay * (2 ** attempt if exponential_backoff else 1)
            logging.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)

# Data Validation
def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Validate that all required fields are present in data
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
    Returns:
        bool: True if all required fields are present
    """
    return all(field in data for field in required_fields)

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, SummaryIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.vector_stores import MetadataFilters, FilterCondition
from typing import List, Optional


def get_doc_tools(
    file_path: str,
    name: str,
) -> str:
    """Get vector query and summary query tools from a document."""

    # load documents
    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
    splitter = SentenceSplitter(chunk_size=1024)
    nodes = splitter.get_nodes_from_documents(documents)
    vector_index = VectorStoreIndex(nodes)
    
    def vector_query(
        query: str, 
        page_numbers: Optional[List[str]] = None
    ) -> str:
        """Use to answer questions over a given paper.
    
        Useful if you have specific questions over the paper.
        Always leave page_numbers as None UNLESS there is a specific page you want to search for.
    
        Args:
            query (str): the string query to be embedded.
            page_numbers (Optional[List[str]]): Filter by set of pages. Leave as NONE 
                if we want to perform a vector search
                over all pages. Otherwise, filter by the set of specified pages.
        
        """
    
        page_numbers = page_numbers or []
        metadata_dicts = [
            {"key": "page_label", "value": p} for p in page_numbers
        ]
        
        query_engine = vector_index.as_query_engine(
            similarity_top_k=2,
            filters=MetadataFilters.from_dicts(
                metadata_dicts,
                condition=FilterCondition.OR
            )
        )
        response = query_engine.query(query)
        return response
        
    
    vector_query_tool = FunctionTool.from_defaults(
        name=f"vector_tool_{name}",
        fn=vector_query
    )
    
    summary_index = SummaryIndex(nodes)
    summary_query_engine = summary_index.as_query_engine(
        response_mode="tree_summarize",
        use_async=True,
    )
    summary_tool = QueryEngineTool.from_defaults(
        name=f"summary_tool_{name}",
        query_engine=summary_query_engine,
        description=(
            f"Useful for summarization questions related to {name}"
        ),
    )

    return vector_query_tool, summary_tool

logger = get_logger(__name__)