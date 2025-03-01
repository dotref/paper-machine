FROM python:3.9-slim

WORKDIR /app

# Upgrade pip for latest features and security
RUN pip install --no-cache-dir pip==23.3.1

# Copy requirements file
COPY requirements/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 \
    --index-url https://download.pytorch.org/whl/cpu

# Install dependencies and verify no conflicts
RUN pip install --no-cache-dir -r requirements.txt \
    && pip check

# Verify key dependencies are installed correctly
RUN python -c 'import fastapi; print(f"FastAPI version: {fastapi.__version__}")' \
    && python -c 'import uvicorn; print(f"Uvicorn version: {uvicorn.__version__}")' \
    && python -c 'import minio; print(f"MinIO version: {minio.__version__}")'

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser

# Switch to non-root user
USER appuser

# Run the application (CMD will be overridden in development)
# Copy source code
COPY src/ /app/src/

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
