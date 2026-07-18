# Use a lightweight Debian image that supports ARM64 native packages
FROM python:3.11-slim-bookworm

# Install system dependencies, Chromium, and the native Chromium Driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker caching layers
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the scraper application code
COPY . .

# Command to execute the sync script when the container runs
CMD ["python", "local_sync.py"]