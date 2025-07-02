# Multi-stage build for optimal production image size
FROM python:3.11-slim as builder

# Build arguments for flexibility
ARG FLASK_ENV=production

# Prevents Python from writing .pyc files and enables unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=${FLASK_ENV}

# Create non-root user for security
RUN addgroup --system --gid 1001 flask && \
    adduser --system --uid 1001 --gid 1001 --no-create-home flask

# Install system dependencies required for psycopg2 and build tools
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system --gid 1001 flask && \
    adduser --system --uid 1001 --gid 1001 --no-create-home flask

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (excluding unnecessary files via .dockerignore)
COPY --chown=flask:flask . .

# Create necessary directories and set permissions
RUN mkdir -p /app/instance /app/logs && \
    chown -R flask:flask /app

# Remove development database files and cache if they exist
RUN rm -f instance/*.db __pycache__ -rf

# Environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV GUNICORN_WORKERS=4
ENV GUNICORN_THREADS=2
ENV GUNICORN_TIMEOUT=120

# Switch to non-root user
USER flask

# Health check using built-in urllib (no additional dependencies)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/', timeout=10)" || exit 1

# Expose port
EXPOSE 5000

# Use gunicorn for production WSGI server
CMD ["sh", "-c", "gunicorn -w ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} -b 0.0.0.0:5000 flask_app:app"]
