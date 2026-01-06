FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /data/keys

# Expose ports
EXPOSE 8545 26656

# Run migrations and start server
CMD alembic upgrade head && \
    python -m src.main
