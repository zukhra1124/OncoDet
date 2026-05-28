FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# System libs needed by OpenCV and Pillow
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python deps first — this layer is cached unless requirements.txt changes
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code into /app
COPY backend/ ./

# Create dirs that may not exist in the repo
RUN mkdir -p uploads logs models

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/api/health || exit 1

CMD ["gunicorn", "--workers", "2", "--timeout", "120", "--bind", "0.0.0.0:5001", "app:create_app()"]
