# Single-container build: Flask serves the API and the static front-end.
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install curl for container health checks.
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy the API application code.
COPY api/__init__.py api/app.py api/auth.py api/db.py api/models.py api/wsgi.py ./api/

# Copy the front-end static files into /app so Flask serves them at /.
COPY index.html styles.css public-api.js public.js logo-header.png ./
COPY admin/ ./admin/

# Create directory for SQLite database persistence.
RUN mkdir -p /app/data

# Default to SQLite for local persistence; set DATABASE_URL for MSSQL/Postgres.
ENV DATABASE=/app/data/dictionary.db
ENV PORT=8000
ENV AUTH_DISABLED=true

EXPOSE 8000

# gunicorn serves both the API and static files via the Flask app.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 wsgi:app --chdir /app/api"]
