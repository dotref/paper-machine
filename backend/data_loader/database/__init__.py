from typing import Type
from .db_handler import DatabaseHandler, MockDatabaseHandler

# Default database handler
default_handler: Type[DatabaseHandler] = MockDatabaseHandler

# Function to get database handler instance
def get_db_handler(handler_type: Type[DatabaseHandler] = None) -> DatabaseHandler:
    """
    Get a database handler instance.
    Args:
        handler_type: The type of database handler to use.
                     If None, uses the default handler.
    Returns:
        An instance of DatabaseHandler
    """
    handler = handler_type or default_handler
    return handler()

# List of available database handlers
# TODO: Add more handlers as they are implemented
available_handlers = {
    'mock': MockDatabaseHandler,
    # 'vector': VectorDatabaseHandler,  # TODO: Future implementation
}

__all__ = [
    'DatabaseHandler',
    'MockDatabaseHandler',
    'get_db_handler',
    'available_handlers',
]