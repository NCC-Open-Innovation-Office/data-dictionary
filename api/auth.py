"""Provider-agnostic authentication and authorization.

This module implements a three-tier access model that works with any
reverse-proxy / SSO front end (Cloudflare Access, oauth2-proxy, nginx
auth_request, your own OIDC, etc.). The app itself never validates the
upstream identity provider's token -- it trusts a set of headers that
the reverse proxy is expected to strip/overwrite before forwarding to
the app. This keeps the app portable across identity providers.

Roles
-----
public  -- unauthenticated; read-only access to GET endpoints.
viewer  -- authenticated by the proxy; can read everything (including
           the full /api/backup export) but cannot write.
admin   -- authenticated and on the admin allow-list; full read/write.

Configuration (environment variables)
-------------------------------------
AUTH_TRUSTED_EMAIL_HEADER
    Header the proxy sets with the authenticated user's email.
    Default: Cf-Access-Authenticated-User-Email (Cloudflare Access).

ADMIN_EMAILS
    Comma-separated allow-list of emails granted the admin role.
    Whitespace around each entry is trimmed. Example:
        ADMIN_EMAILS=alice@ncc.edu, bob@ncc.edu

AUTH_DISABLED
    When 'true' (default in tests), auth is bypassed and every request
    is treated as anonymous/public. The /api/auth/me endpoint returns
    role=public. Set AUTH_DISABLED=false in any real deployment that
    sits behind an authenticating proxy.
"""

import os

from flask import g
from flask import jsonify
from flask import request


PUBLIC = 'public'
VIEWER = 'viewer'
ADMIN = 'admin'

WRITE_METHODS = frozenset({'POST', 'PUT', 'DELETE', 'PATCH'})

PUBLIC_ENDPOINTS = frozenset({
    'health_check',
    'get_config',
    'get_entries',
    'get_entry',
    'get_history',
    'get_tags',
    'get_owners',
    'get_stewards',
    'get_entry_links',
    'get_entry_definitions',
})

# Endpoints that require at least viewer (authenticated) access but are
# still read-only (e.g. full export).
VIEWER_ENDPOINTS = frozenset({
    'backup_database',
    'auth_me',
})


def _trusted_email_header():
    return os.environ.get(
        'AUTH_TRUSTED_EMAIL_HEADER',
        'Cf-Access-Authenticated-User-Email',
    )


def _admin_emails():
    raw = os.environ.get('ADMIN_EMAILS', '')
    return {
        email.strip().lower()
        for email in raw.split(',')
        if email.strip()
    }


def auth_disabled():
    return os.environ.get('AUTH_DISABLED', 'true').lower() == 'true'


def current_email():
    """The authenticated user's email, or None if anonymous."""
    if auth_disabled():
        return None
    return request.headers.get(_trusted_email_header()) or None


def current_role():
    """The resolved role for the current request."""
    email = current_email()
    if not email:
        return PUBLIC
    if email.lower() in _admin_emails():
        return ADMIN
    return VIEWER


def require_auth(required_role):
    """Decorator enforcing a minimum role on a Flask view.

    Returns 401 for missing identity, 403 for insufficient role.
    """
    def decorator(view):
        from functools import wraps

        @wraps(view)
        def wrapper(*args, **kwargs):
            role = current_role()
            if required_role == ADMIN and role != ADMIN:
                if role == PUBLIC:
                    return jsonify(
                        {'error': 'Authentication required'}
                    ), 401
                return jsonify(
                    {'error': 'Administrator access required'}
                ), 403
            if required_role == VIEWER and role == PUBLIC:
                return jsonify(
                    {'error': 'Authentication required'}
                ), 401
            return view(*args, **kwargs)
        return wrapper
    return decorator


def register_auth(app):
    """Install the before_request guard and the /api/auth/me endpoint."""

    @app.before_request
    def _enforce_auth():
        # In test/standalone mode, auth is fully bypassed.
        if auth_disabled():
            g.auth_email = None
            g.auth_role = PUBLIC
            return None

        endpoint = request.endpoint
        method = request.method

        # Public read endpoints: always allowed, anonymous permitted.
        if endpoint in PUBLIC_ENDPOINTS and method not in WRITE_METHODS:
            g.auth_email = current_email()
            g.auth_role = current_role()
            return None

        # Write endpoints always require admin.
        if method in WRITE_METHODS:
            role = current_role()
            if role != ADMIN:
                if role == PUBLIC:
                    return jsonify(
                        {'error': 'Authentication required'}
                    ), 401
                return jsonify(
                    {'error': 'Administrator access required'}
                ), 403
            g.auth_email = current_email()
            g.auth_role = ADMIN
            return None

        # Everything else (viewer-gated GETs like backup, auth/me).
        role = current_role()
        if role == PUBLIC and endpoint in VIEWER_ENDPOINTS:
            return jsonify({'error': 'Authentication required'}), 401
        g.auth_email = current_email()
        g.auth_role = role
        return None

    @app.route('/api/auth/me', methods=['GET'])
    def auth_me():
        email = current_email()
        return jsonify({
            'email': email,
            'role': current_role(),
            'authenticated': email is not None,
        })