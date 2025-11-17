# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app.py .

# Create directory for SQLite database
RUN mkdir -p /app/data

# Set environment variable for database location
ENV DATABASE=/app/data/dictionary.db
ENV PORT=5001

# Expose port
EXPOSE 5001

# Run the application
CMD ["python", "app.py"]
