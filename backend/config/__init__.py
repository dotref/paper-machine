from pathlib import Path
from dotenv import load_dotenv
from .settings import config

# Load environment variables from .env file
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)

# Validate configuration
config.validate()

__all__ = ['config']