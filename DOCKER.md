# Docker Deployment Guide

## Quick Start

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

2. **Access the application:**
   - Public view: http://localhost:8000
   - Admin view: http://localhost:8000/admin/
   - API: http://localhost:5001/api

3. **Stop the application:**
   ```bash
   docker-compose down
   ```

## Services

### Frontend (Port 8000)
- Nginx serving static HTML, CSS, and JavaScript
- Public and admin interfaces

### API (Port 5001)
- Flask REST API
- SQLite database
- Data persisted in `./data/` directory

## Configuration

### Change Ports
Edit `docker-compose.yml`:
```yaml
services:
  frontend:
    ports:
      - "YOUR_PORT:80"  # Change 8000 to your desired port
  api:
    ports:
      - "YOUR_PORT:5000"  # Change 5001 to your desired port
```

### Database Location
By default, the database is stored in `./data/dictionary.db` on your host machine, which persists even if containers are removed.

## Production Deployment

### Update API URL
Before building for production, update the API URLs in:
- `public-api.js` - Change `apiBase` to your production API URL
- `admin/admin-api.js` - Change `apiBase` to your production API URL

### Build for Production
```bash
# Build images
docker-compose build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Restart services
docker-compose restart
```

### Docker Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs api
docker-compose logs frontend

# Rebuild after code changes
docker-compose up -d --build

# Remove all containers and volumes
docker-compose down -v

# Access container shell
docker exec -it data-dictionary-api sh
docker exec -it data-dictionary-frontend sh
```

## Backup Database

```bash
# Backup
cp ./data/dictionary.db ./data/dictionary.db.backup

# Restore
cp ./data/dictionary.db.backup ./data/dictionary.db
docker-compose restart api
```

## Environment Variables

Set in `docker-compose.yml` under `api.environment`:
- `PORT` - API port (default: 5000)
- `DATABASE` - Database file path (default: /app/data/dictionary.db)

## Troubleshooting

### API not responding
```bash
docker-compose logs api
docker-compose restart api
```

### Frontend not loading
```bash
docker-compose logs frontend
docker-compose restart frontend
```

### Database issues
```bash
# Check database file
ls -la ./data/

# Reset database (WARNING: deletes all data)
rm ./data/dictionary.db
docker-compose restart api
```

### Health Check
```bash
curl http://localhost:5001/api/health
```
