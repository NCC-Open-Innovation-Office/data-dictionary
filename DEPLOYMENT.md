# Deployment Guide

## Overview

The Data Dictionary runs as a **single container**. Flask serves both
the static front-end (public and admin interfaces) and the REST API,
so there is no separate web server. Put your own reverse proxy / SSO
front end in front of the container to handle TLS termination and
inject the authenticated-user header.

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
| `ADMIN_EMAILS` | *(empty)* | Comma-separated allow-list of emails granted the `admin` role. Example: `ADMIN_EMAILS=alice@ncc.edu,bob@ncc.edu` |
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

3. **Stop:**
   ```bash
   docker compose down
   ```

### Production configuration

For production, set `AUTH_DISABLED=false` and `ADMIN_EMAILS` in your
compose environment:

```yaml
services:
  data-dictionary:
    environment:
      - AUTH_DISABLED=false
      - ADMIN_EMAILS=alice@ncc.edu,bob@ncc.edu
      - AUTH_TRUSTED_EMAIL_HEADER=X-Forwarded-Email  # match your proxy
```

## Putting a Reverse Proxy in Front

The app expects your reverse proxy to terminate TLS and inject the
authenticated user's email as a header. A minimal example with
**oauth2-proxy** (or any proxy that sets `X-Forwarded-Email`):

1. Run the proxy on 443, forwarding to the container on 8000.
2. Configure it to set `X-Forwarded-Email` from the OIDC session.
3. Set `AUTH_TRUSTED_EMAIL_HEADER=X-Forwarded-Email` and
   `AUTH_DISABLED=false` on the app.

A minimal **Caddy** example (with a placeholder auth plugin):

```
dictionary.example.com {
    reverse_proxy localhost:8000
}
```

Replace the auth layer with whatever your organization uses. The app
itself is agnostic to the choice.

## Data Persistence

By default the SQLite database is stored in `./data/dictionary.db` and
persists across container restarts. To use MSSQL or PostgreSQL instead,
set `DATABASE_URL` (see `DOCKER.md`).

## Troubleshooting

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
