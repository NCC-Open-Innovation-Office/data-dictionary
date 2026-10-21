# Deployment Guide

## Overview

The Data Dictionary runs as a **single container**. Flask serves both
the static front-end (public and admin interfaces) and the REST API,
so there is no separate web server. Put your own reverse proxy / SSO
front end (Caddy, Traefik, oauth2-proxy, etc.) in front of the
container to handle TLS termination and inject the authenticated-user
header.

- **Public view** (`/`) — read-only access for everyone
- **Admin interface** (`/admin/`) — management UI, gated by the access
  role resolved from the authenticated-user header

## Access Roles

| Role | Who | Can do |
|------|-----|--------|
| **public** | Anonymous (no auth) | Read all `GET` endpoints: browse, search, view entries, tags, history |
| **viewer** | Authenticated by the proxy, not on the admin allow-list | Everything public can do, plus the admin panel in **read-only** mode and `/api/backup` |
| **admin** | Authenticated and on the `ADMIN_EMAILS` allow-list | Everything — create/update/delete entries, tags, definitions, links, bulk import, restore |

The role is resolved by the API from the reverse proxy's
authenticated-user header, so the app works with **any** SSO proxy
(oauth2-proxy, nginx auth_request, Caddy, Traefik, etc.) without code
changes.

### API configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_DISABLED` | `true` | When `true`, auth is bypassed and all requests are treated as `public` (the default for tests and standalone local dev). Set to `false` in any deployment behind an authenticating proxy. |
| `ADMIN_EMAILS` | *(empty)* | Comma-separated list of emails granted the `admin` role. Example: `ADMIN_EMAILS=alice@ncc.edu,bob@ncc.edu` |
| `AUTH_TRUSTED_EMAIL_HEADER` | `Cf-Access-Authenticated-User-Email` | The request header carrying the authenticated user's email. Override for your proxy (e.g. `X-Forwarded-Email` for oauth2-proxy). |

The proxy must overwrite this header before forwarding to the app; the
app trusts whatever the proxy sets. Never expose the app directly to
untrusted networks without a proxy in front.

### `GET /api/auth/me`

Returns the current user's resolved role:

```json
{ "email": "alice@ncc.edu", "role": "admin", "authenticated": true }
```

The admin UI calls this on load to gate the interface: non-admin users
get a read-only view with the edit/delete buttons hidden.

## Deploy with Docker Compose

1. **Start the application:**
   ```bash
   docker compose up -d
   ```

2. **Access it:**
   - Public view: http://localhost:8000/
   - Admin view: http://localhost:8000/admin/
   - API: http://localhost:8000/api

3. **Check health:**
   ```bash
   curl http://localhost:8000/api/health
   ```

### Production configuration

```bash
docker compose -f docker-compose.prod.yml up -d
```

The production compose file pulls the published image from GitHub
Container Registry and disables the built-in auth bypass. Set
`ADMIN_EMAILS` to grant write access:

```yaml
environment:
  - AUTH_DISABLED=false
  - ADMIN_EMAILS=alice@ncc.edu,bob@ncc.edu
```

## Putting a Reverse Proxy in Front

The app trusts the authenticated-user header, so the proxy in front of
it is responsible for authenticating the user and overwriting that
header. Replace the auth layer with whatever your organization uses. The app
itself is agnostic to the choice.

## Data Persistence

By default the SQLite database is stored in `./data/dictionary.db` and
persists across container restarts. To use MSSQL or PostgreSQL instead,
set `DATABASE_URL` (see `DOCKER.md`).

### SELinux hosts

The compose files mount the data directory with the `:z` option:

```yaml
volumes:
  - ./data:/app/data:z
```

On a host with SELinux enabled (RHEL, CentOS, Fedora), a container
cannot read a host directory that carries a normal home-directory
label. Without `:z` the app fails at startup with:

```
sqlite3.OperationalError: unable to open database file
```

The `:z` option relabels `./data` so the container can access it. It is
ignored on hosts without SELinux, so the same compose file works on
both. Note that `:z` changes the SELinux label on the host directory.

## Troubleshooting

### App exits immediately with "unable to open database file"
- On a SELinux host, the data directory needs the `:z` mount option.
  See "SELinux hosts" above.

### Admin shows read-only for everyone
- `AUTH_DISABLED` is still `true` (the default). Set it to `false` and
  ensure your proxy is forwarding the authenticated-user header.
- `ADMIN_EMAILS` is empty or doesn't include your email. Add it
  (lowercase, comma-separated).

### Everyone gets 401 on write endpoints
- The trusted-email header name doesn't match what your proxy sets.
  Set `AUTH_TRUSTED_EMAIL_HEADER` to match.

### API is wide open
- You're running with `AUTH_DISABLED=true` and no proxy in front. Set
  `AUTH_DISABLED=false` and put an authenticating proxy in front of the
  container.
