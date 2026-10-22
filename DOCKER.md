# Docker Deployment Guide

## Quick Start

1. **Build and run with Docker Compose:**
   ```bash
   docker compose up -d
   ```

2. **Access the application:**
   - Public view: http://localhost:8000/
   - Admin view: http://localhost:8000/admin/
   - API: http://localhost:8000/api

3. **Stop the application:**
   ```bash
   docker compose down
   ```

## Architecture

The app runs as a **single container**. Flask serves both the static
front-end (public and admin HTML/CSS/JS) and the REST API, so there is
no separate web server or reverse proxy in the default deployment.

Put your own reverse proxy / SSO front end (Caddy, Traefik, oauth2-proxy,
an internal nginx, a cloud load balancer, etc.) in front of the
container to handle TLS termination and inject the authenticated-user
header (see "Access roles" below).

## Configuration

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `8000` | Port the app listens on |
| `DATABASE` | `/app/data/dictionary.db` | SQLite file path |
| `DATABASE_URL` | *(unset)* | SQLAlchemy URL for MSSQL/Postgres (overrides `DATABASE`) |
| `AUTH_DISABLED` | `false` | Bypass auth (set `true` only for local, single-user development) |
| `SSOUSER_HEADER` | `SSOUSER` | Header carrying the authenticated user's email |
| `PROXY_SHARED_SECRET` | *(empty)* | Shared secret the proxy must present; the app ignores the identity header without it |
| `AUTH_TRUSTED_SECRET_HEADER` | `X-Proxy-Secret` | Header carrying that shared secret |
| `ADMIN_EMAILS` | *(empty)* | Comma-separated admin email allow-list (bootstrap / break-glass) |
| `VIEWER_EMAILS` | *(empty)* | Comma-separated viewer email allow-list (bootstrap / break-glass) |
| `SSO_AUTO_PROVISION` | `true` | Create a user record on first sign-in |
| `ALLOW_DD_ID_EDIT` | `false` | Allow DD ID editing in the admin panel |

### Change the port
Edit `docker-compose.yml`:
```yaml
services:
  data-dictionary:
    ports:
      - "YOUR_PORT:8000"
```

### Database location
By default, the SQLite database is stored in `./data/dictionary.db` on
your host, which persists across container restarts. To use MSSQL or
PostgreSQL instead, set `DATABASE_URL`:

```yaml
services:
  data-dictionary:
    environment:
      - DATABASE_URL=mssql+pymssql://user:pass@sqlserver:1433/data_dictionary
      # or: postgresql+psycopg2://user:pass@postgres:5432/data_dictionary
```

## Production Deployment

```bash
# Build the image
docker compose build

# Run in detached mode
docker compose up -d

# View logs
docker compose logs -f
```

### Access roles

The app supports three tiers (see `DEPLOYMENT.md` for the full table):
**public** (anonymous read), **viewer** (authenticated read-only), and
**admin** (full write). Role is resolved from a trusted email header set
by your reverse proxy plus the `ADMIN_EMAILS` allow-list. Set
`AUTH_DISABLED=false` and configure `ADMIN_EMAILS` in production.

The role actually comes from the group memberships stored in the
database and managed from **Admin → Manage Users**. A person's first
sign-in creates their record automatically and places them in the
`viewers` group; an administrator promotes them to `admins` when they
need edit rights. `ADMIN_EMAILS` remains available as a bootstrap and
break-glass path.

In production, set `AUTH_DISABLED=false` and `PROXY_SHARED_SECRET`. The
secret is what stops anyone who can reach the container from becoming
an administrator by setting the identity header themselves.

## Database Integration Testing

The compose file includes disposable database services behind profiles.

```bash
# MSSQL
docker compose --profile mssql-test up -d sqlserver
RUN_MSSQL_TESTS=true python -m unittest integration_tests.test_api_integration
docker compose --profile mssql-test down

# PostgreSQL
docker compose --profile postgres-test up -d postgres
RUN_POSTGRES_TESTS=true python -m unittest integration_tests.test_api_integration
docker compose --profile postgres-test down
```

### Useful Docker commands

```bash
docker compose ps
docker compose logs data-dictionary
docker compose up -d --build      # rebuild after code changes
docker compose down -v
docker exec -it data-dictionary sh
```

## Backup Database

```bash
# Backup
cp ./data/dictionary.db ./data/dictionary.db.backup

# Restore
cp ./data/dictionary.db.backup ./data/dictionary.db
docker compose restart data-dictionary
```
