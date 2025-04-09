FROM python:3.9-slim

WORKDIR /app

# Upgrade pip for security and latest features
RUN pip install --no-cache-dir pip==23.3.1

# Copy requirements file
COPY requirements/requirements.txt ./requirements.txt

# Install CPU-only torch and torchvision
RUN pip install --no-cache-dir \
    torch==2.1.1 \
    torchvision==0.16.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Install stable and compatible versions of sentence-transformers and huggingface_hub
RUN pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    "transformers==4.29.0" \
    "huggingface_hub<0.14"

# Install remaining Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip check

# Verify installation of critical packages
RUN python -c 'import fastapi; print(f"✅ FastAPI version: {fastapi.__version__}")' \
    && python -c 'import uvicorn; print(f"✅ Uvicorn version: {uvicorn.__version__}")' \
    && python -c 'import minio; print(f"✅ MinIO version: {minio.__version__}")' \
    && python -c 'import sentence_transformers; print("✅ SentenceTransformers is installed and importable")'

# Copy entrypoint script and make it executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create and switch to non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Copy backend source code
COPY src/ /app/src/

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Start FastAPI server with autoreload (for development)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]