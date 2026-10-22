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

## Identity

The app never validates the identity provider's token. It trusts a
header that the reverse proxy sets after authenticating the person:

| Header | Default | Carries |
|--------|---------|---------|
| `SSOUSER` | `SSOUSER` | The authenticated person's email address, e.g. `alice@ncc.edu` |
| `X-Proxy-Secret` | `X-Proxy-Secret` | A shared secret the proxy presents, matched against `PROXY_SHARED_SECRET` |

The proxy must **overwrite** these headers before forwarding to the
app. Never expose the app directly to an untrusted network: without a
proxy in front, anyone can set the header themselves and become an
administrator.

> **Set `PROXY_SHARED_SECRET` in every real deployment.** When it is
> set, the app ignores the `SSOUSER` header unless the matching secret
> is also present. That closes the header-spoofing hole for
> deployments where the container might be reachable by something
> other than the proxy.

## Access Roles

| Role | Who | Can do |
|------|-----|--------|
| **public** | Anonymous (no auth) | Read the public endpoints: browse, search, view entries, tags, history |
| **viewer** | Signed in, in the `viewers` group | Everything public can do, plus the admin panel in **read-only** mode and `/api/backup` |
| **admin** | Signed in, in the `admins` group | Everything — create/update/delete entries, tags, definitions, links, bulk import, restore, and manage users |

Group membership lives in the **database** and is managed from the
admin interface (**Admin → Manage Users**). The role is derived from
the groups a person belongs to, so there is one source of truth.

### First sign-in

When a person signs in through SSO and no user record exists for their
email address, the app **creates one automatically** and places them in
the `viewers` group. An administrator then promotes them to `admins`
if they need edit rights.

If a record already exists — because an administrator seeded it ahead
of time — the sign-in **merges** into that record: no duplicate row
is created, the group memberships are preserved, and only the sign-in
timestamp and a previously-empty display name are refreshed.

### API configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_DISABLED` | `true` | When `true`, auth is bypassed and all requests are treated as `public` (the default for tests and standalone local dev). Set to `false` in any deployment behind an authenticating proxy. |
| `SSOUSER_HEADER` | `SSOUSER` | The request header carrying the authenticated user's email. |
| `AUTH_TRUSTED_SECRET_HEADER` | `X-Proxy-Secret` | The request header carrying the proxy's shared secret. |
| `PROXY_SHARED_SECRET` | *(empty)* | The shared secret the proxy must present. When empty, the identity header is trusted on its own — acceptable only where the proxy is the sole route to the app. |
| `ADMIN_EMAILS` | *(empty)* | Comma-separated allow-list of emails granted the `admin` role. Acts as a **bootstrap and break-glass override**: it can raise a role, never lower one, and it cannot resurrect a deactivated user. |
| `VIEWER_EMAILS` | *(empty)* | Comma-separated allow-list of emails granted the `viewer` role, with the same override semantics. |
| `SSO_AUTO_PROVISION` | `true` | When `true`, a first-time sign-in creates a user record in the `viewers` group. Set to `false` to require an administrator to seed every user by hand. |
| `SSO_USER_ID_HEADER` | `SSOUSERID` | Optional header carrying a stable subject identifier from the identity provider. It is stored on the user record. |

### `GET /api/auth/me`

Returns the current user's resolved role:

```json
{
  "email": "alice@ncc.edu",
  "role": "admin",
  "authenticated": true,
  "user": {
    "id": 3,
    "email": "alice@ncc.edu",
    "displayName": "Alice Smith",
    "active": true,
    "groups": ["viewers", "admins"],
    "role": "admin",
    "lastLoginAt": "2026-10-21T14:02:11.123456"
  }
}
```

The endpoint is readable by anonymous callers, who get
`"role": "public"`, so the front end can tell "not signed in" from
"signed in without access".

The admin UI calls this on load to gate the interface: non-admin users
get a read-only view with the edit/delete buttons hidden.

## Managing Users

Administrators manage access from **Admin → Manage Users**:

- **Add User** — seed an email address ahead of its first sign-in, and
  choose the groups it belongs to.
- **Make Viewer / Remove Viewer** — grant or revoke read access to the
  authenticated area.
- **Make Admin / Remove Admin** — grant or revoke edit rights.
- **Remove** — delete the user record entirely.

The last administrator cannot be removed, demoted, or deactivated,
because doing so would leave the deployment with nobody able to manage
it. Use `ADMIN_EMAILS` as the break-glass path if that ever happens.

### User API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/users` | List users and their groups (admin only) |
| `POST` | `/api/users` | Seed a user: `{"email": "...", "groups": ["viewers", "admins"]}` |
| `PUT` | `/api/users/<id>` | Update a user's groups, display name, or active flag |
| `DELETE` | `/api/users/<id>` | Remove a user record |



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

For production, set `AUTH_DISABLED=false`, `PROXY_SHARED_SECRET`, and
`ADMIN_EMAILS` in your compose environment:

```yaml
services:
  data-dictionary:
    environment:
      - AUTH_DISABLED=false
      - PROXY_SHARED_SECRET=change-me-to-a-long-random-value
      - ADMIN_EMAILS=alice@ncc.edu,bob@ncc.edu
      # - SSOUSER_HEADER=X-Forwarded-Email  # match your proxy
```

The proxy must overwrite the identity header before forwarding to the
app; the app trusts whatever the proxy sets. Never expose the app
directly to untrusted networks without a proxy in front.

`PROXY_SHARED_SECRET` is the important one: it stops anyone who can
reach the container from becoming an administrator just by setting a
header.

## Putting a Reverse Proxy in Front

The app expects your reverse proxy to terminate TLS and inject the
authenticated user's email as a header. A minimal example with
**oauth2-proxy** (or any proxy that sets `X-Forwarded-Email`):

1. Run the proxy on 443, forwarding to the container on 8000.
2. Configure it to set `X-Forwarded-Email` from the OIDC session, and
   to set `X-Proxy-Secret` to the shared secret.
3. Set `SSOUSER_HEADER=X-Forwarded-Email`,
   `AUTH_TRUSTED_SECRET_HEADER=X-Proxy-Secret`,
   `PROXY_SHARED_SECRET=<the same secret>`, and `AUTH_DISABLED=false`
   on the app.

If your proxy always uses the default header names, you can skip the
header-name settings and only set `PROXY_SHARED_SECRET` and
`AUTH_DISABLED=false`.

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
- The person is not in the `admins` group. Open **Admin → Manage
  Users** and use **Make Admin**.
- `ADMIN_EMAILS` is empty and doesn't include their email. Add it
  (lowercase, comma-separated) as a bootstrap, or promote them in the
  admin interface.

### Everyone gets 401 on write endpoints
- The identity header name doesn't match what your proxy sets. Set
  `SSOUSER_HEADER` to match.
- `PROXY_SHARED_SECRET` is set but the proxy is not sending the
  matching secret. Set `AUTH_TRUSTED_SECRET_HEADER` to the header your
  proxy uses, or make the proxy send the secret.

### Everyone is treated as signed out
- `PROXY_SHARED_SECRET` is set and the proxy is not sending it, so the
  app ignores the identity header. Check the proxy's secret header
  name against `AUTH_TRUSTED_SECRET_HEADER`.

### A user cannot sign in
- Check **Admin → Manage Users**: the record may be deactivated, or the
  person may have no group membership.
- If `SSO_AUTO_PROVISION=false`, an unknown email address gets no
  record at all. Seed the user from the admin interface first.

### API is wide open
- You're running with `AUTH_DISABLED=true` and no proxy in front. Set
  `AUTH_DISABLED=false` and put an authenticating proxy in front of the
  container.
