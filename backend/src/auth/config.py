import os

# Security configuration
SECRET_KEY = os.environ.get("AUTH_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60