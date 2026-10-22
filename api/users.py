"""User provisioning and group membership.

This module owns everything that reads or writes records in the
``users`` and ``user_groups`` tables. The auth layer asks it two
questions on every request:

* who is this person? (:func:`provision_or_merge_user`)
* what may they do?  (:func:`resolve_role`)

Keeping that here means the request-scoped auth code stays small and
the rules about "what a role means" live in one place.

Role model
----------
A user's role is *derived* from their group memberships rather than
stored on the user row, so there is a single source of truth:

* ``viewers``  -> may read the authenticated area
* ``admins``   -> may read and edit

A user may hold both; ``admins`` wins. Environment variables
(``ADMIN_EMAILS`` / ``VIEWER_EMAILS``) act as a bootstrap and
break-glass override: they can only *raise* a role, never lower one.
"""

import os

from sqlalchemy import func

try:
    from api.models import GROUP_ADMINS
    from api.models import GROUP_VIEWERS
    from api.models import ROLE_ADMIN
    from api.models import ROLE_NONE
    from api.models import ROLE_RANK
    from api.models import ROLE_VIEWER
    from api.models import User
    from api.models import UserGroup
except ImportError:
    from models import GROUP_ADMINS
    from models import GROUP_VIEWERS
    from models import ROLE_ADMIN
    from models import ROLE_NONE
    from models import ROLE_RANK
    from models import ROLE_VIEWER
    from models import User
    from models import UserGroup


# A person who signs in for the first time is placed in this group so
# they can use the authenticated area straight away. Administrators
# then promote them to 'admins' through the admin UI.
DEFAULT_PROVISION_GROUP = GROUP_VIEWERS


def normalize_email(email):
    """Normalize an email for storage and comparison."""
    if not email:
        return ''
    return email.strip().lower()


def _email_list(name):
    raw = os.environ.get(name, '')
    return {
        item.strip().lower()
        for item in raw.split(',')
        if item.strip()
    }


def env_admin_emails():
    return _email_list('ADMIN_EMAILS')


def env_viewer_emails():
    return _email_list('VIEWER_EMAILS')


def env_role_for(email):
    """Role granted by environment overrides, or ``none``.

    These lists are the bootstrap and break-glass path: they can grant
    access when the database has no record yet, and they can restore
    access if the admin UI is unreachable.
    """
    normalized = normalize_email(email)
    if not normalized:
        return ROLE_NONE
    if normalized in env_admin_emails():
        return ROLE_ADMIN
    if normalized in env_viewer_emails():
        return ROLE_VIEWER
    return ROLE_NONE


def auto_provision_enabled():
    """Whether a first-time sign-in creates a record with access."""
    return (
        os.environ.get('SSO_AUTO_PROVISION', 'true').lower() == 'true'
    )


def find_user(session, email):
    """Look up a user by email, case-insensitively."""
    normalized = normalize_email(email)
    if not normalized:
        return None
    return (
        session.query(User)
        .filter(func.lower(User.email) == normalized)
        .first()
    )


def get_user_by_id(session, user_id):
    return session.get(User, user_id)


def provision_or_merge_user(
    session,
    email,
    *,
    display_name=None,
    sso_subject=None,
    timestamp=None,
):
    """Create the user on first sign-in, or merge into the existing one.

    "Merge" means: the record that already exists for this email is
    kept as-is (including its group memberships and its identity), and
    only the volatile fields are refreshed -- the SSO subject, the
    display name when it was previously empty, and the last-login
    timestamp. No duplicate row is created.
    """
    normalized = normalize_email(email)
    if not normalized:
        return None, False

    now = timestamp
    user = find_user(session, normalized)
    created = False

    if user is None:
        created = True
        user = User(
            email=normalized,
            display_name=display_name or '',
            active=1,
            sso_subject=sso_subject or '',
            createdAt=now,
            updatedAt=now,
            lastLoginAt=now,
            createdBy=normalized,
            updatedBy=normalized,
        )
        session.add(user)
        session.flush()

        if auto_provision_enabled():
            add_user_to_group(
                session,
                user,
                DEFAULT_PROVISION_GROUP,
                created_by=normalized,
                timestamp=now,
            )
        return user, created

    # Existing record: refresh only what a login should change.
    if sso_subject and not user.sso_subject:
        user.sso_subject = sso_subject
    if display_name and not user.display_name:
        user.display_name = display_name
    user.lastLoginAt = now
    user.updatedAt = now
    user.updatedBy = normalized
    return user, created


def add_user_to_group(session, user, group_name, *, created_by, timestamp):
    """Add a user to a group. Returns True when the row was created."""
    existing = (
        session.query(UserGroup)
        .filter(
            UserGroup.user_id == user.id,
            UserGroup.group_name == group_name,
        )
        .first()
    )
    if existing is not None:
        return False
    session.add(
        UserGroup(
            group_name=group_name,
            user_id=user.id,
            createdAt=timestamp,
            createdBy=created_by or '',
        )
    )
    session.flush()
    return True


def remove_user_from_group(session, user, group_name):
    """Remove a user from a group. Returns True when a row was removed."""
    membership = (
        session.query(UserGroup)
        .filter(
            UserGroup.user_id == user.id,
            UserGroup.group_name == group_name,
        )
        .first()
    )
    if membership is None:
        return False
    session.delete(membership)
    session.flush()
    return True


def groups_for_user(session, user):
    return sorted(
        {membership.group_name for membership in user.groups},
        key=lambda name: (name != GROUP_ADMINS, name),
    )


def role_from_groups(group_names):
    """Map a set of group names to a role. ``admins`` wins."""
    role = ROLE_NONE
    for name in group_names:
        if name == GROUP_ADMINS:
            candidate = ROLE_ADMIN
        elif name == GROUP_VIEWERS:
            candidate = ROLE_VIEWER
        else:
            continue
        if ROLE_RANK[candidate] > ROLE_RANK[role]:
            role = candidate
    return role


def resolve_role(session, email):
    """The effective role for an email address.

    Order of precedence:

    1. A deactivated user is refused outright -- no group membership
       and no environment override can restore access.
    2. Group membership in the database.
    3. Environment overrides, which may only raise the role.
    """
    normalized = normalize_email(email)
    if not normalized:
        return ROLE_NONE

    user = find_user(session, normalized)
    if user is not None:
        if not user.active:
            return ROLE_NONE
        db_role = role_from_groups(groups_for_user(session, user))
        env_role = env_role_for(normalized)
        if ROLE_RANK[env_role] > ROLE_RANK[db_role]:
            return env_role
        return db_role

    # No record yet: only an environment override can grant access.
    return env_role_for(normalized)


def user_to_dict(user, session=None):
    """Serialize a user for the API.

    The reported role is the *effective* role: the role from group
    membership, raised by an environment override if one applies. It
    must agree with the role the auth layer resolves for the same
    person, otherwise the admin interface would show a different
    answer from the one the API enforces.
    """
    groups = groups_for_user(session, user) if session is not None else []
    db_role = role_from_groups(groups)
    env_role = env_role_for(user.email)
    effective = db_role
    if ROLE_RANK[env_role] > ROLE_RANK[db_role]:
        effective = env_role
    if not user.active:
        # A deactivated user has no access at all, even if an
        # environment override would otherwise grant one.
        effective = ROLE_NONE

    payload = {
        'id': user.id,
        'email': user.email,
        'displayName': user.display_name or '',
        'active': bool(user.active),
        'groups': groups,
        'role': effective,
        'createdAt': user.createdAt,
        'updatedAt': user.updatedAt,
        'lastLoginAt': user.lastLoginAt,
        'createdBy': user.createdBy or '',
        'updatedBy': user.updatedBy or '',
    }
    return payload
