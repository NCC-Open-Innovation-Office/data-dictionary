"""Provider-agnostic authentication and authorization.

The app never validates the upstream identity provider's token. It
trusts a set of headers that the reverse proxy is expected to
strip/overwrite before forwarding to the app. This keeps the app
portable across identity providers (Cloudflare Access, oauth2-proxy,
nginx auth_request, a campus SSO proxy, or your own).

Identity
--------
``SSOUSER`` carries the authenticated person's email address. It is
the single source of truth for *who* the caller is.

Because the app trusts that header completely, it must never be
reachable except through a proxy that overwrites it. Two mechanisms
enforce that:

* ``PROXY_SHARED_SECRET`` -- the proxy also sends a shared secret in
  the header named by ``AUTH_TRUSTED_SECRET_HEADER``. When that
  variable is set, an identity header is only believed if the secret
  matches. Set it in every real deployment.
* ``AUTH_DISABLED`` -- an explicit local-development escape hatch.

Roles
-----
public  -- unauthenticated; read-only access to the public endpoints.
viewer  -- authenticated and in the 'viewers' group (or named by
           ``VIEWER_EMAILS``); can read everything, including the full
           /api/backup export, but cannot write.
admin   -- authenticated and in the 'admins' group (or named by
           ``ADMIN_EMAILS``); full read/write.

Group membership lives in the database and is managed in the admin
interface. On a first successful sign-in a user record is created
automatically (see ``api/users.py``).

Configuration (environment variables)
-------------------------------------
SSOUSER_HEADER
    Header the proxy sets with the authenticated user's email.
    Default: SSOUSER.

AUTH_TRUSTED_SECRET_HEADER
    Header carrying the proxy's shared secret. Default: X-Proxy-Secret.

PROXY_SHARED_SECRET
    The shared secret the proxy must present. When unset, the identity
    header is trusted on its own -- acceptable only on a private
    network where the proxy is the sole path to the app.

ADMIN_EMAILS
    Comma-separated allow-list of emails granted the admin role.
    Acts as a bootstrap and break-glass override: it can raise a
    role, never lower one.

VIEWER_EMAILS
    Comma-separated allow-list of emails granted the viewer role.

SSO_AUTO_PROVISION
    When 'true' (the default), a first-time sign-in creates a user
    record and places it in the 'viewers' group.

AUTH_DISABLED
    When 'true' (default in tests), auth is bypassed and every request
    is treated as anonymous/public. Set to false in any real deployment
    that sits behind an authenticating proxy.

SSO_USER_ID_HEADER
    Optional header carrying a stable subject identifier from the
    identity provider. It is stored on the user record so a provider
    that issues a subject id can be linked later.
"""

import hmac
import os

from flask import g
from flask import jsonify
from flask import request

try:
    from api.models import ROLE_ADMIN
    from api.models import ROLE_VIEWER
except ImportError:
    from models import ROLE_ADMIN
    from models import ROLE_VIEWER


PUBLIC = 'public'
VIEWER = 'viewer'
ADMIN = 'admin'

WRITE_METHODS = frozenset({'POST', 'PUT', 'DELETE', 'PATCH'})

# Endpoints that are readable by anyone, including anonymous callers.
# Everything NOT listed here requires at least a viewer, so a newly
# added endpoint fails closed rather than open.
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
    # The "who am I" probe is safe to expose: it returns the caller's
    # own role and nothing about anyone else. An anonymous caller gets
    # role=public rather than a 401, so the front end can tell
    # "not signed in" from "signed in without access".
    'auth_me',
    # The front-end shells and their assets must load for anonymous
    # visitors; the public dictionary view is a public page.
    'index',
    'static_asset',
    'admin_shell',
})

# Endpoints that require at least viewer (authenticated) access but are
# still read-only (e.g. the full export).
VIEWER_ENDPOINTS = frozenset({
    'backup_database',
})

# Read-only endpoints that expose administrative data. They are not
# writes, so the generic write rule does not cover them; they are
# listed here so they require the admin role.
ADMIN_ENDPOINTS = frozenset({
    'list_users',
})


def _header(name, default):
    return os.environ.get(name, default)


def sso_user_header():
    return _header('SSOUSER_HEADER', 'SSOUSER')


def trusted_secret_header():
    return _header('AUTH_TRUSTED_SECRET_HEADER', 'X-Proxy-Secret')


def proxy_shared_secret():
    return os.environ.get('PROXY_SHARED_SECRET', '').strip()


def auth_disabled():
    return os.environ.get('AUTH_DISABLED', 'true').lower() == 'true'


def _secret_is_valid():
    """Is the proxy's shared secret present and correct?

    When no secret is configured the identity header is trusted on its
    own. That is only safe when the proxy is the only route to the
    app, so the deployment documentation insists on it.
    """
    expected = proxy_shared_secret()
    if not expected:
        return True
    provided = request.headers.get(trusted_secret_header()) or ''
    return hmac.compare_digest(provided.strip(), expected)


def current_email():
    """The authenticated user's email, or None if anonymous.

    Returns None when auth is disabled, when the shared secret does
    not validate, or when no identity header is present.
    """
    if auth_disabled():
        return None
    if not _secret_is_valid():
        return None
    raw = request.headers.get(sso_user_header())
    if raw is None:
        return None
    email = raw.strip()
    return email.lower() or None


def current_sso_subject():
    """Optional stable subject id supplied by the identity provider."""
    if auth_disabled():
        return None
    raw = request.headers.get(
        _header('SSO_USER_ID_HEADER', 'SSOUSERID')
    )
    if raw is None:
        return None
    return raw.strip() or None


def current_role():
    """The resolved role for the current request."""
    email = current_email()
    if not email:
        return PUBLIC
    return _resolve_role_for_email(email)


def _resolve_role_for_email(email):
    """Resolve a role from the database plus environment overrides.

    Falls back to the environment allow-lists when the database is
    unreachable so a proxy misconfiguration never locks every
    administrator out of a running deployment.
    """
    try:
        from api.users import resolve_role
    except ImportError:
        from users import resolve_role

    try:
        from flask import current_app
        database = current_app.extensions.get('dd_db')
        if database is not None:
            with database.session_scope() as session:
                role = resolve_role(session, email)
            if role == ROLE_ADMIN:
                return ADMIN
            if role == ROLE_VIEWER:
                return VIEWER
            return PUBLIC
    except Exception:
        # Database unavailable: fall back to the environment allow-lists
        # so the deployment stays administrable.
        pass

    try:
        from api.users import env_role_for
    except ImportError:
        from users import env_role_for

    env_role = env_role_for(email)
    if env_role == ROLE_ADMIN:
        return ADMIN
    if env_role == ROLE_VIEWER:
        return VIEWER
    return PUBLIC


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


def _utcnow_iso():
    from datetime import datetime
    from datetime import timezone

    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def provision_on_login(app):
    """Create or merge the user record for an authenticated request.

    Called on every authenticated request. The first sign-in creates
    the record and places the person in the default group; later
    sign-ins merge into the existing record without duplicating it.
    """
    try:
        from api.users import provision_or_merge_user
    except ImportError:
        from users import provision_or_merge_user

    email = current_email()
    if not email:
        return None

    try:
        from flask import current_app
        database = current_app.extensions.get('dd_db')
        if database is None:
            return None
        with database.session_scope() as session:
            user, _created = provision_or_merge_user(
                session,
                email,
                sso_subject=current_sso_subject(),
                timestamp=_utcnow_iso(),
            )
            return user
    except Exception:
        # Provisioning must never break the request; the role is
        # resolved separately and can still come from the environment.
        return None


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

        # Establish the identity and make sure the user record exists
        # *before* the role is resolved. A first-time sign-in has no
        # record yet, and provisioning places them in the default
        # group; resolving the role first would reject that very
        # first request.
        email = current_email()
        g.auth_email = email
        if email is not None:
            provision_on_login(app)

        # Public read endpoints: always allowed, anonymous permitted.
        if endpoint in PUBLIC_ENDPOINTS and method not in WRITE_METHODS:
            g.auth_role = current_role()
            return None

        # Administrative reads (e.g. the user list) require admin even
        # though they are not writes.
        if endpoint in ADMIN_ENDPOINTS:
            role = current_role()
            if role != ADMIN:
                if role == PUBLIC:
                    return jsonify(
                        {'error': 'Authentication required'}
                    ), 401
                return jsonify(
                    {'error': 'Administrator access required'}
                ), 403
            g.auth_role = ADMIN
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
            g.auth_role = ADMIN
            return None

        # Everything else (viewer-gated GETs like backup, auth/me, and
        # any endpoint that is not on the public list). Unknown GETs
        # fail closed: they require at least a viewer.
        role = current_role()
        if role == PUBLIC:
            return jsonify({'error': 'Authentication required'}), 401
        g.auth_role = role
        return None

    @app.route('/api/auth/me', methods=['GET'])
    def auth_me():
        email = current_email()
        role = current_role()
        user = None
        if email:
            try:
                from api.users import find_user
                from api.users import user_to_dict
            except ImportError:
                from users import find_user
                from users import user_to_dict
            try:
                from flask import current_app
                database = current_app.extensions.get('dd_db')
                if database is not None:
                    with database.session_scope() as session:
                        record = find_user(session, email)
                        if record is not None:
                            user = user_to_dict(record, session)
            except Exception:
                user = None
        return jsonify({
            'email': email,
            'role': role,
            'authenticated': email is not None,
            'user': user,
        })
