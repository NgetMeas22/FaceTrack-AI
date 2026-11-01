# ==============================================================================
# FaceTrack AI — Production Dockerfile for Hostinger VPS & Container Deployments
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install OS dependencies required by OpenCV and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and models
COPY app/ app/
COPY ml_models/ ml_models/
COPY download_models.py .
COPY README.md .

# Download face models if not present
RUN python download_models.py

# Create data directories for SQLite database and employee avatar uploads
RUN mkdir -p data/uploads

# Expose port (Hostinger default or custom 8000)
EXPOSE 8000

# Run uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

