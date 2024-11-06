from .data_models import Document, QueryResult, ModelConfig

# Export all data models
__all__ = [
    'Document',
    'QueryResult',
    'ModelConfig'
]

# Optionally add model validation functions
def validate_document(doc: Document) -> bool:
    """
    Validate document structure and content
    Args:
        doc: Document instance to validate
    Returns:
        bool: True if valid, False otherwise
    """
    # TODO: Implement validation logic
    pass

def validate_query_result(result: QueryResult) -> bool:
    """
    Validate query result structure and content
    Args:
        result: QueryResult instance to validate
    Returns:
        bool: True if valid, False otherwise
    """
    # TODO: Implement validation logic
    pass

# Add validation functions to exports if needed
__all__ += ['validate_document', 'validate_query_result']