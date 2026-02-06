FROM python:3.12-slim

# Basic env hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (optional but often helpful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY REST.py .

# Create non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 5055

# Simple healthcheck hitting your GET /data
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5055/data').read()" || exit 1

# Run via gunicorn (1-2 workers is often enough for tiny ingest; tune if needed)
CMD ["gunicorn", "-b", "0.0.0.0:5055", "REST:app", "--workers=2", "--threads=4", "--timeout=60"]