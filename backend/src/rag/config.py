
import os 

OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

SYSTEM_PROMPT = """
You are a helpful assistant that provides accurate information based on the given context.
"""

LIMIT_RETRIEVED_CHUNKS = 5
SIMILARITY_THRESHOLD = 0.7