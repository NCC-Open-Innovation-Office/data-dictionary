# Data Dictionary Platform 🏗️

A modern web-based data dictionary platform for managing organizational terms, definitions, and data standards. Features a clean public interface for browsing and an admin interface for content management.

## ✨ Features

- **Public Interface**: Browse and search dictionary entries with filtering by type and reports
- **Admin Interface**: Full CRUD operations for entries and report management
- **Tagging System**: Organize entries with color-coded reports (tags)
- **Change History**: Track all modifications with timestamps and discussions
- **Docker Ready**: Containerized for easy deployment
- **SQLAlchemy Persistence**: Shared persistence layer for SQLite and MSSQL
- **REST API**: Full API access for integrations

## 🚀 Quick Start

### Using Published Images (Recommended)

1. **Download the production compose file:**
   ```bash
   curl -o docker-compose.prod.yml https://raw.githubusercontent.com/marshalmiller/data-dictionary/main/docker-compose.prod.yml
   ```

2. **Create data directory:**
   ```bash
   mkdir -p data
   ```

3. **Start the application:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Access the application:**
   - Public view: http://localhost:8000/
   - Admin view: http://localhost:8000/admin/
   - API: http://localhost:8000/api

### Using Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/marshalmiller/data-dictionary.git
   cd data-dictionary
   ```

2. **Start with Docker:**
   ```bash
   docker compose up -d
   ```

   Or use the start script:
   ```bash
   ./start.sh
   ```

## 🔐 Default Credentials

**Admin Login:**
- Username: `admin`
- Password: `admin123`

> ⚠️ **Security Note**: Change these credentials in production!

## 📚 Usage

### Public Interface
- **Search**: Find entries by term, definition, or abbreviation
- **Filter**: Filter by data type or report category
- **Browse**: View all dictionary entries in a clean, organized table

### Admin Interface
- **Entry Management**: Add, edit, and delete dictionary entries
- **Report Management**: Create and manage color-coded report categories
- **Change Tracking**: All modifications are logged with timestamps
- **Export**: Download data as CSV for external use

### API Endpoints

- `GET /api/entries` - Get all entries (public)
- `GET /api/tags` - Get all reports/tags (public)
- `GET /api/health` - Health check
- `POST /api/entries` - Create entry (admin)
- `PUT /api/entries/{id}` - Update entry (admin)
- `DELETE /api/entries/{id}` - Delete entry (admin)
- `GET /api/history` - Get change history (admin)

## 🏗️ Architecture

````
┌─────────────────────────────────────────────────┐
│            Flask app (single container)         │
│   Static front-end + REST API, port 8000        │
└─────────────────────────────────────────────────┘
                        │
               ┌─────────────────┐
               │ SQLAlchemy DB   │
               │ SQLite/MSSQL/   │
               │ PostgreSQL       │
               └─────────────────┘
````

A reverse proxy / SSO front end (Caddy, Traefik, oauth2-proxy, etc.)
sits in front of the container for TLS termination and auth-header
injection in production.

## 🔧 Configuration

### Environment Variables

- `PORT`: app port (default: 8000)
- `DATABASE`: SQLite file path shorthand (default: /app/data/dictionary.db)
- `DATABASE_URL`: Full SQLAlchemy connection URL. Examples: `mssql+pymssql://username:password@sqlserver:1433/data_dictionary`, `postgresql+psycopg2://username:password@postgres:5432/data_dictionary`
- `AUTH_DISABLED`: bypass auth (default: `true`; set `false` behind a proxy)
- `ADMIN_EMAILS`: comma-separated admin email allow-list
- `AUTH_TRUSTED_EMAIL_HEADER`: header carrying the authenticated email (default: `Cf-Access-Authenticated-User-Email`)

### Volume Mounts

- `./data:/app/data` - Persists the SQLite database when `DATABASE_URL` is not set

## 📦 Docker Image

The image is automatically built and published to GitHub Container Registry:

- `ghcr.io/marshalmiller/data-dictionary:latest`

### Available Tags
- `latest` - Latest stable release
- `main` - Latest development build
- `v*.*.*` - Semantic version tags
- `sha-*` - Commit-specific builds

## 🛠️ Development

### Prerequisites
- Docker and Docker Compose
- Python 3.12+ (for local development)

### Local Development Setup

1. **Clone and enter directory:**
   ```bash
   git clone https://github.com/marshalmiller/data-dictionary.git
   cd data-dictionary
   ```

2. **Start development environment:**
   ```bash
   # Using Docker (recommended)
   docker compose up -d
   
   # Or run locally (Flask serves both the API and the front-end)
   cd api && pip install -r requirements.txt
   python wsgi.py
   ```

### Building the Image Locally

```bash
docker compose build
```

### Integration Tests

Run the API integration suite against SQLite:

```bash
python -m unittest integration_tests.test_api_integration
```

Run the same suite against SQLite and the disposable SQL Server profile:

```bash
docker compose --profile mssql-test up -d sqlserver
RUN_MSSQL_TESTS=true python -m unittest integration_tests.test_api_integration
docker compose --profile mssql-test down
```

## 🔄 Updates and Maintenance

### Updating to Latest Version
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Backup Data
```bash
# Backup SQLite database
cp data/dictionary.db data/dictionary.db.backup

# Or backup entire data directory
tar -czf data-backup-$(date +%Y%m%d).tar.gz data/
```

### View Logs
```bash
# All services
docker compose logs -f

# The app container
docker compose logs -f data-dictionary
```

## 🚦 Monitoring

### Health Checks
- App health endpoint: `http://localhost:8000/api/health`
- Docker health check: Built into the container

### Troubleshooting

**App Connection Issues:**
1. Check if the container is running: `docker compose ps`
2. Check logs: `docker compose logs data-dictionary`
3. Verify health: `curl http://localhost:8000/api/health`

### MSSQL Configuration

Set `DATABASE_URL` on the API service or in your shell to point at SQL Server:

```bash
export DATABASE_URL="mssql+pymssql://username:password@sqlserver:1433/data_dictionary"
```

If `DATABASE_URL` is unset, the API continues to use the existing SQLite file defined by `DATABASE`.

**Frontend Issues:**
1. Check nginx logs: `docker compose logs frontend`
2. Verify files are served: `curl http://localhost:8000`

## 📄 License

GPL-3.0 License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker
5. Submit a pull request

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review container logs for error messages

---

Built with ❤️ for better data documentation and organizational knowledge management.