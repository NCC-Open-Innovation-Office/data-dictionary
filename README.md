# Data Dictionary Platform 🏗️

A modern web-based data dictionary platform for managing organizational terms, definitions, and data standards. Features a clean public interface for browsing and an admin interface for content management.

## ✨ Features

- **Public Interface**: Browse and search dictionary entries with filtering by type and reports
- **Admin Interface**: Full CRUD operations for entries and report management
- **Tagging System**: Organize entries with color-coded reports (tags)
- **Change History**: Track all modifications with timestamps and discussions
- **Docker Ready**: Containerized for easy deployment
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
   - Public view: http://localhost:8000
   - Admin view: http://localhost:8000/admin/
   - API: http://localhost:5001/api

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

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │
│   (nginx)       │◄──►│   (Flask)       │
│   Port 8000     │    │   Port 5001     │
└─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │   (Persistent)  │
                       └─────────────────┘
```

## 🔧 Configuration

### Environment Variables

**API Container:**
- `PORT`: API server port (default: 5001)
- `DATABASE`: Database file path (default: /app/data/dictionary.db)

### Volume Mounts

- `./data:/app/data` - Persists SQLite database

## 📦 Docker Images

Images are automatically built and published to GitHub Container Registry:

- **Frontend**: `ghcr.io/marshalmiller/data-dictionary-frontend:latest`
- **API**: `ghcr.io/marshalmiller/data-dictionary-api:latest`

### Available Tags
- `latest` - Latest stable release
- `main` - Latest development build
- `v*.*.*` - Semantic version tags
- `sha-*` - Commit-specific builds

## 🛠️ Development

### Prerequisites
- Docker and Docker Compose
- Python 3.12+ (for local development)
- Node.js (optional, for frontend development)

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
   
   # Or run locally
   cd api && pip install -r requirements.txt
   python app.py &
   cd .. && python -m http.server 8000
   ```

### Building Images Locally

```bash
# Build both images
docker compose build

# Build specific image
docker compose build frontend
docker compose build api
```

## 🔄 Updates and Maintenance

### Updating to Latest Version
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Backup Data
```bash
# Backup database
cp data/dictionary.db data/dictionary.db.backup

# Or backup entire data directory
tar -czf data-backup-$(date +%Y%m%d).tar.gz data/
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f frontend
```

## 🚦 Monitoring

### Health Checks
- API health endpoint: `http://localhost:5001/api/health`
- Docker health check: Built into API container

### Troubleshooting

**API Connection Issues:**
1. Check if API container is running: `docker compose ps`
2. Check API logs: `docker compose logs api`
3. Verify health: `curl http://localhost:5001/api/health`

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