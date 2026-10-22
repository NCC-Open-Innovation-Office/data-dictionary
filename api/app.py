from datetime import datetime
from datetime import timezone
import json
import os

from flask import current_app
from flask import Flask
from flask import g
from flask import jsonify
from flask import request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

try:
    from api.auth import register_auth
    from api.db import Database
    from api.models import ChangeHistory
    from api.models import Entry
    from api.models import EntryDefinition
    from api.models import EntryLink
    from api.models import EntryTag
    from api.models import GROUP_ADMINS
    from api.models import KNOWN_GROUPS
    from api.models import Tag
    from api.models import User
except ImportError:
    from auth import register_auth
    from db import Database
    from models import ChangeHistory
    from models import Entry
    from models import EntryDefinition
    from models import EntryLink
    from models import EntryTag
    from models import GROUP_ADMINS
    from models import KNOWN_GROUPS
    from models import Tag
    from models import User


def utcnow_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def parse_json_field(value):
    if not value:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def json_string(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def optional_json_body():
    """Return the request's JSON body, or an empty dict if there isn't one.

    `request.json` raises a 415 when the Content-Type is not JSON and a
    400 when the body is not valid JSON, so it cannot be combined with
    `or {}` to mean "the body is optional". This helper tolerates a
    missing, empty, or malformed body and simply returns {}.

    Endpoints that require fields (for example `data['tag_id']`) still
    fail loudly with a KeyError, which the route handlers translate into
    a 400 response.
    """
    if not request.is_json:
        return {}
    try:
        data = request.get_json(silent=True)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def normalize_classification(value):
    classification = value or 'public'
    if classification == 'private':
        return 'internal'
    return classification


def entry_to_dict(entry, include_related=False):
    payload = {
        'id': entry.id,
        'term': entry.term,
        'definition': entry.definition,
        'abbreviation': entry.abbreviation or '',
        'dataType': entry.dataType or '',
        'inputFormat': entry.inputFormat or '',
        'variations': entry.variations or '',
        'owner': entry.owner or '',
        'stewards': entry.stewards or '',
        'classification': entry.classification or 'public',
        'discussion': entry.discussion or '',
        'ddId': entry.ddId or '',
        'createdAt': entry.createdAt,
        'updatedAt': entry.updatedAt,
    }
    if include_related:
        payload['tags'] = [
            tag_to_dict(tag)
            for tag in sorted(
                entry.tags,
                key=lambda item: item.name.lower(),
            )
        ]
        payload['links'] = [
            {
                'link_id': link.id,
                'target_entry_id': link.target_entry_id,
                'link_type': link.link_type,
                'target_term': (
                    link.target_entry.term if link.target_entry else None
                ),
            }
            for link in sorted(
                entry.outgoing_links,
                key=lambda item: item.id,
            )
        ]
        payload['report_definitions'] = [
            entry_definition_to_dict(definition)
            for definition in sorted(
                entry.definitions,
                key=lambda item: (
                    item.tag.name.lower() if item.tag else '',
                    item.id,
                ),
            )
        ]
    return payload


def tag_to_dict(tag):
    return {
        'id': tag.id,
        'name': tag.name,
        'color': tag.color,
        'createdAt': tag.createdAt,
    }


def entry_definition_to_dict(definition):
    return {
        'id': definition.id,
        'tag_id': definition.tag_id,
        'definition': definition.definition,
        'tag_name': definition.tag.name if definition.tag else None,
        'tag_color': definition.tag.color if definition.tag else None,
    }


def history_to_dict(item):
    return {
        'id': item.id,
        'timestamp': item.timestamp,
        'action': item.action,
        'term': item.term,
        'oldData': parse_json_field(item.oldData),
        'newData': parse_json_field(item.newData),
        'discussion': item.discussion,
        'user': item.user,
    }


def get_database():
    return current_app.extensions['dd_db']


def _map_without_static(url_map):
    """Return a copy of the URL map with Flask's static rule removed.

    Flask registers ``/<path:filename>`` -> ``static`` automatically
    when a static folder is configured, and that rule serves any file
    under the folder. Rebuilding the map without it keeps the URL
    matching logic inside Werkzeug instead of relying on private
    attributes.
    """
    from werkzeug.routing import Map

    rules = [
        rule
        for rule in url_map.iter_rules()
        if rule.endpoint != 'static'
    ]
    new_map = Map(
        rules,
        default_subdomain=url_map.default_subdomain,
        strict_slashes=url_map.strict_slashes,
        merge_slashes=url_map.merge_slashes,
        redirect_defaults=url_map.redirect_defaults,
        converters=dict(url_map.converters),
        sort_parameters=url_map.sort_parameters,
        sort_key=url_map.sort_key,
        host_matching=url_map.host_matching,
    )
    new_map.host_matching = url_map.host_matching
    return new_map


# The only files the web server will hand out. Everything else in the
# project tree -- the SQLite database, the Python sources, the .git
# directory, the compose files -- is invisible to HTTP clients.
STATIC_ASSETS = frozenset({
    'index.html',
    'styles.css',
    'public-api.js',
    'public.js',
    'logo-header.png',
    'admin/index.html',
    'admin/admin-api.js',
    'admin/admin.js',
})


def _looks_like_project_file(filename):
    """Does this path name a real file in the project tree?

    Some project files have no extension (``Dockerfile``, ``LICENSE``).
    Without this check a request for ``/Dockerfile`` would be treated
    as an application route and answered with the SPA shell.
    """
    project_root = current_app.static_folder
    if not project_root or '/' in filename:
        return False
    candidate = os.path.join(project_root, filename)
    try:
        return os.path.isfile(candidate)
    except OSError:
        return False


def serve_static_asset(relative_path):
    """Serve a front-end asset from the allow-list, or raise 404.

    Two protections are in play. The allow-list means an unlisted file
    cannot be fetched at all, and the resolved path is confirmed to sit
    inside the project root so a crafted path cannot escape it.

    A 404 is raised rather than returned so the SPA fallback handler
    can decide between the application shell and a genuine error.
    """
    from flask import abort

    if relative_path not in STATIC_ASSETS:
        abort(404)

    project_root = current_app.static_folder
    if not project_root:
        abort(404)

    target = os.path.abspath(os.path.join(project_root, relative_path))
    root = os.path.abspath(project_root)
    if os.path.commonpath([root, target]) != root:
        abort(404)
    if not os.path.isfile(target):
        abort(404)

    return current_app.send_static_file(relative_path)


def not_found_response():
    """A 404 that the SPA fallback will not turn into a shell."""
    return jsonify({'error': 'Not found'}), 404


def current_user():
    """The authenticated user's email, falling back to the request body.

    Resolution order:
    1. Email set by the auth layer (g.auth_email) -- the proxy-authenticated
       user when AUTH_DISABLED=false.
    2. A 'user' field in the JSON request body -- preserves existing
       client behaviour (e.g. the admin UI sending user: 'Admin').
    3. 'Admin' so change history is never blank.
    """
    email = getattr(g, 'auth_email', None)
    if email:
        return email
    payload = request.get_json(silent=True) or {}
    return payload.get('user') or 'Admin'


def allow_dd_id_edit():
    return current_app.config['ALLOW_DD_ID_EDIT']


def _users_module():
    """Import the user helpers, tolerating both package layouts."""
    try:
        from api import users as users_module
    except ImportError:
        import users as users_module
    return users_module


def user_to_dict(user, session=None):
    return _users_module().user_to_dict(user, session)


def find_user(session, email):
    return _users_module().find_user(session, email)


def add_user_to_group(session, user, group_name, *, created_by, timestamp):
    return _users_module().add_user_to_group(
        session,
        user,
        group_name,
        created_by=created_by,
        timestamp=timestamp,
    )


def remove_user_from_group(session, user, group_name):
    return _users_module().remove_user_from_group(session, user, group_name)


def _has_other_admin(session, user):
    """Is there an administrator other than ``user``?

    Used to stop the last administrator from being removed, which
    would leave the deployment unmanageable. A user who is not an
    administrator in the first place does not need this check.
    """
    if not _is_admin(session, user):
        return True

    for other in session.query(User).all():
        if other.id == user.id:
            continue
        if not other.active:
            continue
        if _is_admin(session, other):
            return True

    # An environment override also counts as an administrator, because
    # that person can still sign in and administer the deployment.
    try:
        from api.users import env_admin_emails
    except ImportError:
        from users import env_admin_emails
    env_admins = env_admin_emails()
    if user.email.lower() in env_admins:
        # This user is an admin by virtue of the environment list, so
        # removing the record does not lock the deployment out -- but
        # only if some other address is also listed.
        return len(env_admins) > 1
    return False


def _is_admin(session, user):
    """Does this user hold the admin role right now?"""
    if not user.active:
        return False
    groups = {membership.group_name for membership in user.groups}
    if GROUP_ADMINS in groups:
        return True
    try:
        from api.users import env_admin_emails
    except ImportError:
        from users import env_admin_emails
    return user.email.lower() in env_admin_emails()


def create_history_record(
    session,
    *,
    action,
    term,
    old_data,
    new_data,
    discussion,
    user,
):
    session.add(
        ChangeHistory(
            timestamp=utcnow_iso(),
            action=action,
            term=term,
            oldData=json_string(old_data),
            newData=json_string(new_data),
            discussion=discussion or '',
            user=user or 'Admin',
        )
    )


def create_app(database_url=None, initialize=True, testing=False):
    # The front-end files live in the project root (one level above the
    # api package). Resolve that directory so Flask can serve them.
    api_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(api_dir)

    app = Flask(
        __name__,
        static_folder=project_root,
        static_url_path='',
    )
    app.config['TESTING'] = testing
    app.config['ALLOW_DD_ID_EDIT'] = (
        os.environ.get('ALLOW_DD_ID_EDIT', 'false').lower() == 'true'
    )

    # Flask auto-registers a catch-all static route that maps any URL
    # straight onto a file under the static folder. That would serve
    # the SQLite database, the Python sources, and the .git directory
    # to anyone who can reach the port, so the route is removed and
    # replaced by an allow-listed handler in register_routes().
    #
    # The route is removed by rebuilding the map with the static rule
    # filtered out, which avoids poking at Werkzeug internals.
    app.url_map = _map_without_static(app.url_map)

    database = Database(database_url=database_url, testing=testing)
    app.extensions['dd_db'] = database
    app.teardown_appcontext(lambda exception: database.remove())
    if initialize:
        database.init_db()

    register_auth(app)
    register_routes(app)
    return app


def register_routes(app):
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok', 'message': 'API is running'})

    @app.route('/api/config', methods=['GET'])
    def get_config():
        return jsonify({'allowDdIdEdit': allow_dd_id_edit()})

    @app.route('/api/entries', methods=['GET'])
    def get_entries():
        try:
            with get_database().session_scope() as session:
                entries = (
                    session.query(Entry)
                    .options(
                        selectinload(Entry.tags),
                        selectinload(Entry.outgoing_links).selectinload(
                            EntryLink.target_entry
                        ),
                        selectinload(Entry.definitions).selectinload(
                            EntryDefinition.tag
                        ),
                    )
                    .order_by(Entry.term.asc())
                    .all()
                )
                return jsonify(
                    [
                        entry_to_dict(entry, include_related=True)
                        for entry in entries
                    ]
                )
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>', methods=['GET'])
    def get_entry(entry_id):
        try:
            with get_database().session_scope() as session:
                entry = session.get(Entry, entry_id)
                if not entry:
                    return jsonify({'error': 'Entry not found'}), 404
                return jsonify(entry_to_dict(entry))
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries', methods=['POST'])
    def create_entry():
        try:
            data = optional_json_body()
            now = utcnow_iso()
            entry = Entry(
                term=data['term'],
                definition=data['definition'],
                abbreviation=data.get('abbreviation', ''),
                dataType=data.get('dataType', ''),
                inputFormat=data.get('inputFormat', ''),
                variations=data.get('variations', ''),
                owner=data.get('owner', ''),
                stewards=data.get('stewards', ''),
                classification=normalize_classification(
                    data.get('classification', 'public')
                ),
                discussion=data.get('discussion', ''),
                ddId=(
                    data.get('ddId', '') if allow_dd_id_edit() else ''
                ),
                createdAt=now,
                updatedAt=now,
            )

            with get_database().session_scope() as session:
                session.add(entry)
                session.flush()
                create_history_record(
                    session,
                    action='create',
                    term=entry.term,
                    old_data=None,
                    new_data=data,
                    discussion=data.get('discussion', ''),
                    user=current_user(),
                )
                return jsonify(
                    {
                        'id': entry.id,
                        'message': 'Entry created successfully',
                    }
                ), 201
        except (KeyError, TypeError) as exc:
            return jsonify({'error': str(exc)}), 400
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>', methods=['PUT'])
    def update_entry(entry_id):
        try:
            data = optional_json_body()
            now = utcnow_iso()

            with get_database().session_scope() as session:
                entry = session.get(Entry, entry_id)
                if not entry:
                    return jsonify({'error': 'Entry not found'}), 404

                old_data = entry_to_dict(entry)
                entry.term = data['term']
                entry.definition = data['definition']
                entry.abbreviation = data.get('abbreviation', '')
                entry.dataType = data.get('dataType', '')
                entry.inputFormat = data.get('inputFormat', '')
                entry.variations = data.get('variations', '')
                entry.owner = data.get('owner', '')
                entry.stewards = data.get('stewards', '')
                entry.classification = normalize_classification(
                    data.get('classification', 'public')
                )
                entry.discussion = data.get('discussion', '')
                if allow_dd_id_edit():
                    entry.ddId = data.get('ddId', old_data.get('ddId', ''))
                entry.updatedAt = now

                create_history_record(
                    session,
                    action='update',
                    term=entry.term,
                    old_data=old_data,
                    new_data=data,
                    discussion=data.get('discussion', ''),
                    user=current_user(),
                )
                return jsonify({'message': 'Entry updated successfully'})
        except (KeyError, TypeError) as exc:
            return jsonify({'error': str(exc)}), 400
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
    def delete_entry(entry_id):
        try:
            payload = optional_json_body()
            with get_database().session_scope() as session:
                entry = session.get(Entry, entry_id)
                if not entry:
                    return jsonify({'error': 'Entry not found'}), 404

                entry_data = entry_to_dict(entry)
                term = entry.term
                session.delete(entry)
                create_history_record(
                    session,
                    action='delete',
                    term=term,
                    old_data=entry_data,
                    new_data=None,
                    discussion=payload.get('discussion', ''),
                    user=current_user(),
                )
                return jsonify({'message': 'Entry deleted successfully'})
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/history', methods=['GET'])
    def get_history():
        try:
            with get_database().session_scope() as session:
                history = (
                    session.query(ChangeHistory)
                    .order_by(ChangeHistory.timestamp.desc())
                    .all()
                )
                return jsonify([history_to_dict(item) for item in history])
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/tags', methods=['GET'])
    def get_tags():
        try:
            with get_database().session_scope() as session:
                tags = session.query(Tag).order_by(Tag.name.asc()).all()
                return jsonify([tag_to_dict(tag) for tag in tags])
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/tags', methods=['POST'])
    def create_tag():
        try:
            data = optional_json_body()
            tag = Tag(
                name=data['name'],
                color=data.get('color', '#004C8E'),
                createdAt=utcnow_iso(),
            )
            with get_database().session_scope() as session:
                session.add(tag)
                session.flush()
                return jsonify(
                    {
                        'id': tag.id,
                        'message': 'Tag created successfully',
                    }
                ), 201
        except (KeyError, TypeError) as exc:
            return jsonify({'error': str(exc)}), 400
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
    def delete_tag(tag_id):
        try:
            with get_database().session_scope() as session:
                tag = session.get(Tag, tag_id)
                if not tag:
                    return jsonify({'error': 'Tag not found'}), 404
                session.delete(tag)
                return jsonify({'message': 'Tag deleted successfully'})
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/tags', methods=['POST'])
    def add_entry_tag(entry_id):
        try:
            data = optional_json_body()
            with get_database().session_scope() as session:
                entry = session.get(Entry, entry_id)
                tag = session.get(Tag, data['tag_id'])
                if not entry:
                    return jsonify({'error': 'Entry not found'}), 404
                if not tag:
                    return jsonify({'error': 'Tag not found'}), 404

                exists = session.get(
                    EntryTag,
                    {'entry_id': entry_id, 'tag_id': data['tag_id']},
                )
                if not exists:
                    session.add(
                        EntryTag(
                            entry_id=entry_id,
                            tag_id=data['tag_id'],
                        )
                    )

                create_history_record(
                    session,
                    action='tag_added',
                    term=entry.term,
                    old_data=None,
                    new_data={'tag_id': tag.id, 'tag_name': tag.name},
                    discussion='',
                    user=current_user(),
                )
                return jsonify({'message': 'Tag added to entry'})
        except (KeyError, TypeError) as exc:
            return jsonify({'error': str(exc)}), 400
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/tags/<int:tag_id>',
               methods=['DELETE'])
    def remove_entry_tag(entry_id, tag_id):
        try:
            with get_database().session_scope() as session:
                entry = session.get(Entry, entry_id)
                tag = session.get(Tag, tag_id)
                association = session.get(
                    EntryTag,
                    {'entry_id': entry_id, 'tag_id': tag_id},
                )

                if association:
                    session.delete(association)

                if entry and tag:
                    create_history_record(
                        session,
                        action='tag_removed',
                        term=entry.term,
                        old_data={
                            'tag_id': tag.id,
                            'tag_name': tag.name,
                        },
                        new_data=None,
                        discussion='',
                        user=current_user(),
                    )

                return jsonify({'message': 'Tag removed from entry'})
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/owners', methods=['GET'])
    def get_owners():
        try:
            with get_database().session_scope() as session:
                owners = [
                    value
                    for value, in session.query(Entry.owner)
                    .filter(Entry.owner.isnot(None), Entry.owner != '')
                    .distinct()
                    .order_by(Entry.owner.asc())
                    .all()
                ]
                return jsonify(owners)
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/stewards', methods=['GET'])
    def get_stewards():
        try:
            with get_database().session_scope() as session:
                stewards = [
                    value
                    for value, in session.query(Entry.stewards)
                    .filter(Entry.stewards.isnot(None), Entry.stewards != '')
                    .distinct()
                    .order_by(Entry.stewards.asc())
                    .all()
                ]
                return jsonify(stewards)
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/links', methods=['GET'])
    def get_entry_links(entry_id):
        try:
            with get_database().session_scope() as session:
                links = (
                    session.query(EntryLink)
                    .options(selectinload(EntryLink.target_entry))
                    .filter(EntryLink.source_entry_id == entry_id)
                    .order_by(EntryLink.id.asc())
                    .all()
                )
                return jsonify(
                    [
                        {
                            'link_id': link.id,
                            'target_entry_id': link.target_entry_id,
                            'link_type': link.link_type,
                            'target_term': (
                                link.target_entry.term
                                if link.target_entry else None
                            ),
                        }
                        for link in links
                    ]
                )
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/links', methods=['POST'])
    def add_entry_link(entry_id):
        try:
            data = optional_json_body()
            with get_database().session_scope() as session:
                target_entry = session.get(Entry, data['target_entry_id'])
                if not target_entry:
                    return jsonify({'error': 'Target entry not found'}), 404

                link = EntryLink(
                    source_entry_id=entry_id,
                    target_entry_id=data['target_entry_id'],
                    link_type=data.get('link_type', 'see_also'),
                    createdAt=utcnow_iso(),
                )
                session.add(link)
                session.flush()

                return jsonify(
                    {
                        'link_id': link.id,
                        'target_entry_id': data['target_entry_id'],
                        'target_term': target_entry.term,
                        'link_type': link.link_type,
                    }
                ), 201
        except (KeyError, TypeError) as exc:
            return jsonify({'error': str(exc)}), 400
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/links/<int:link_id>',
               methods=['DELETE'])
    def remove_entry_link(entry_id, link_id):
        try:
            with get_database().session_scope() as session:
                link = session.get(EntryLink, link_id)
                if link and link.source_entry_id == entry_id:
                    session.delete(link)
                return jsonify({'message': 'Link removed successfully'})
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/bulk-import', methods=['POST'])
    def bulk_import_entries():
        try:
            data = optional_json_body()
            entries = data.get('entries', [])
            if not entries:
                return jsonify({'error': 'No entries provided'}), 400

            imported = 0
            updated = 0
            skipped = 0
            errors = []

            with get_database().session_scope() as session:
                for item in entries:
                    term = item.get('term', '').strip()
                    try:
                        if not term:
                            skipped += 1
                            continue

                        existing = (
                            session.query(Entry)
                            .filter(Entry.term == term)
                            .one_or_none()
                        )
                        now = utcnow_iso()

                        if existing:
                            existing.definition = item.get('definition', '')
                            existing.abbreviation = item.get(
                                'abbreviation',
                                '',
                            )
                            existing.dataType = item.get('dataType', '')
                            existing.inputFormat = item.get(
                                'inputFormat',
                                '',
                            )
                            existing.variations = item.get(
                                'variations',
                                '',
                            )
                            existing.owner = item.get('owner', '')
                            existing.stewards = item.get('stewards', '')
                            existing.classification = (
                                normalize_classification(
                                    item.get('classification', 'public')
                                )
                            )
                            existing.discussion = item.get(
                                'discussion',
                                '',
                            )
                            existing.ddId = item.get('ddId', '')
                            existing.updatedAt = now
                            entry = existing
                            updated += 1
                        else:
                            entry = Entry(
                                term=term,
                                definition=item.get('definition', ''),
                                abbreviation=item.get('abbreviation', ''),
                                dataType=item.get('dataType', ''),
                                inputFormat=item.get('inputFormat', ''),
                                variations=item.get('variations', ''),
                                owner=item.get('owner', ''),
                                stewards=item.get('stewards', ''),
                                classification=normalize_classification(
                                    item.get('classification', 'public')
                                ),
                                discussion=item.get('discussion', ''),
                                ddId=item.get('ddId', ''),
                                createdAt=now,
                                updatedAt=now,
                            )
                            session.add(entry)
                            session.flush()
                            imported += 1

                        reports_str = item.get('reports', '').strip()
                        if reports_str:
                            tag_names = [
                                tag_name.strip()
                                for tag_name in reports_str.split(',')
                                if tag_name.strip()
                            ]
                            for tag_name in tag_names:
                                tag = (
                                    session.query(Tag)
                                    .filter(Tag.name == tag_name)
                                    .one_or_none()
                                )
                                if not tag:
                                    tag = Tag(
                                        name=tag_name,
                                        color='#004C8E',
                                        createdAt=now,
                                    )
                                    session.add(tag)
                                    session.flush()

                                association = session.get(
                                    EntryTag,
                                    {
                                        'entry_id': entry.id,
                                        'tag_id': tag.id,
                                    },
                                )
                                if not association:
                                    session.add(
                                        EntryTag(
                                            entry_id=entry.id,
                                            tag_id=tag.id,
                                        )
                                    )
                    except (KeyError, TypeError, ValueError) as exc:
                        errors.append(
                            f"Error with term '{term}': {str(exc)}"
                        )
                        skipped += 1

                return jsonify(
                    {
                        'message': 'Import completed',
                        'imported': imported,
                        'updated': updated,
                        'skipped': skipped,
                        'errors': errors,
                    }
                ), 200
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/definitions', methods=['GET'])
    def get_entry_definitions(entry_id):
        try:
            with get_database().session_scope() as session:
                definitions = (
                    session.query(EntryDefinition)
                    .options(selectinload(EntryDefinition.tag))
                    .filter(EntryDefinition.entry_id == entry_id)
                    .join(Tag)
                    .order_by(Tag.name.asc())
                    .all()
                )
                return jsonify(
                    [
                        entry_definition_to_dict(definition)
                        for definition in definitions
                    ]
                )
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/definitions', methods=['POST'])
    def add_entry_definition(entry_id):
        try:
            data = optional_json_body()
            now = utcnow_iso()

            with get_database().session_scope() as session:
                entry = session.get(Entry, entry_id)
                tag = session.get(Tag, data['tag_id'])
                if not entry:
                    return jsonify({'error': 'Entry not found'}), 404
                if not tag:
                    return jsonify({'error': 'Tag not found'}), 404

                existing = (
                    session.query(EntryDefinition)
                    .filter(
                        EntryDefinition.entry_id == entry_id,
                        EntryDefinition.tag_id == data['tag_id'],
                    )
                    .one_or_none()
                )

                if existing:
                    old_definition = existing.definition
                    existing.definition = data['definition']
                    existing.updatedAt = now
                    definition_id = existing.id
                    action = 'report_def_updated'
                    old_data = {
                        'tag_id': tag.id,
                        'tag_name': tag.name,
                        'definition': old_definition,
                    }
                    new_data = {
                        'tag_id': tag.id,
                        'tag_name': tag.name,
                        'definition': data['definition'],
                    }
                else:
                    definition = EntryDefinition(
                        entry_id=entry_id,
                        tag_id=data['tag_id'],
                        definition=data['definition'],
                        createdAt=now,
                        updatedAt=now,
                    )
                    session.add(definition)
                    session.flush()
                    definition_id = definition.id
                    action = 'report_def_added'
                    old_data = None
                    new_data = {
                        'tag_id': tag.id,
                        'tag_name': tag.name,
                        'definition': data['definition'],
                    }

                create_history_record(
                    session,
                    action=action,
                    term=entry.term,
                    old_data=old_data,
                    new_data=new_data,
                    discussion='',
                    user=current_user(),
                )

                return jsonify(
                    {
                        'id': definition_id,
                        'message': 'Definition saved successfully',
                    }
                ), 201
        except (KeyError, TypeError) as exc:
            return jsonify({'error': str(exc)}), 400
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/definitions/<int:def_id>',
               methods=['PUT'])
    def update_entry_definition(entry_id, def_id):
        try:
            data = optional_json_body()
            with get_database().session_scope() as session:
                definition = session.get(EntryDefinition, def_id)
                if not definition or definition.entry_id != entry_id:
                    return jsonify({'error': 'Definition not found'}), 404
                definition.definition = data['definition']
                definition.updatedAt = utcnow_iso()
                return jsonify(
                    {'message': 'Definition updated successfully'}
                )
        except (KeyError, TypeError) as exc:
            return jsonify({'error': str(exc)}), 400
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/entries/<int:entry_id>/definitions/<int:def_id>',
               methods=['DELETE'])
    def delete_entry_definition(entry_id, def_id):
        try:
            with get_database().session_scope() as session:
                definition = (
                    session.query(EntryDefinition)
                    .options(
                        selectinload(EntryDefinition.tag),
                        selectinload(EntryDefinition.entry),
                    )
                    .filter(
                        EntryDefinition.id == def_id,
                        EntryDefinition.entry_id == entry_id,
                    )
                    .one_or_none()
                )
                if not definition:
                    return jsonify(
                        {'message': 'Definition deleted successfully'}
                    )

                create_history_record(
                    session,
                    action='report_def_removed',
                    term=definition.entry.term if definition.entry else '',
                    old_data={
                        'tag_id': (
                            definition.tag.id if definition.tag else None
                        ),
                        'tag_name': (
                            definition.tag.name if definition.tag else ''
                        ),
                        'definition': definition.definition,
                    },
                    new_data=None,
                    discussion='',
                    user=current_user(),
                )
                session.delete(definition)
                return jsonify({'message': 'Definition deleted successfully'})
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------
    # Every route in this block requires the admin role. The auth layer
    # enforces that centrally: any write method needs admin, and
    # 'list_users' is registered as a viewer-gated read that the
    # before_request hook upgrades because it is an admin concern.
    @app.route('/api/users', methods=['GET'])
    def list_users():
        try:
            with get_database().session_scope() as session:
                users = (
                    session.query(User)
                    .order_by(User.email.asc())
                    .all()
                )
                return jsonify({
                    'users': [
                        user_to_dict(user, session) for user in users
                    ],
                    'groups': list(KNOWN_GROUPS),
                })
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/users', methods=['POST'])
    def create_user():
        """Seed a user before their first sign-in.

        An administrator can add an email address ahead of time so
        that, when the person signs in through SSO, the existing
        record is merged rather than created from scratch.
        """
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        if not email or '@' not in email:
            return jsonify({'error': 'A valid email is required'}), 400

        groups = data.get('groups') or []
        if not isinstance(groups, list):
            return jsonify({'error': 'groups must be a list'}), 400
        invalid = [
            name for name in groups if name not in KNOWN_GROUPS
        ]
        if invalid:
            return jsonify({
                'error': (
                    'Unknown group(s): '
                    + ', '.join(str(name) for name in invalid)
                ),
            }), 400

        actor = current_user()
        now = utcnow_iso()
        try:
            with get_database().session_scope() as session:
                user = find_user(session, email)
                created = False
                if user is None:
                    created = True
                    user = User(
                        email=email,
                        display_name=(data.get('displayName') or '').strip(),
                        active=1,
                        sso_subject='',
                        createdAt=now,
                        updatedAt=now,
                        createdBy=actor,
                        updatedBy=actor,
                    )
                    session.add(user)
                    session.flush()
                for name in groups:
                    add_user_to_group(
                        session,
                        user,
                        name,
                        created_by=actor,
                        timestamp=now,
                    )
                return jsonify({
                    'message': (
                        'User created' if created else 'User updated'
                    ),
                    'created': created,
                    'user': user_to_dict(user, session),
                }), 201 if created else 200
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/users/<int:user_id>', methods=['PUT'])
    def update_user(user_id):
        """Change a user's active flag and group membership."""
        data = request.get_json(silent=True) or {}
        actor = current_user()
        now = utcnow_iso()
        try:
            with get_database().session_scope() as session:
                user = session.get(User, user_id)
                if user is None:
                    return jsonify({'error': 'User not found'}), 404

                # Validate everything before changing anything, so a
                # rejected request leaves the record untouched.
                new_groups = None
                if 'groups' in data:
                    new_groups = data.get('groups') or []
                    if not isinstance(new_groups, list):
                        return jsonify(
                            {'error': 'groups must be a list'}
                        ), 400
                    invalid = [
                        name for name in new_groups
                        if name not in KNOWN_GROUPS
                    ]
                    if invalid:
                        return jsonify({
                            'error': (
                                'Unknown group(s): '
                                + ', '.join(
                                    str(name) for name in invalid
                                )
                            ),
                        }), 400

                new_active = None
                if 'active' in data:
                    new_active = 1 if data['active'] else 0

                # Removing the last administrator would leave the
                # deployment with nobody able to manage it.
                if new_active == 0 and not _has_other_admin(session, user):
                    return jsonify({
                        'error': (
                            'Cannot deactivate the last administrator'
                        ),
                    }), 400
                if (
                    new_groups is not None
                    and GROUP_ADMINS not in new_groups
                    and not _has_other_admin(session, user)
                ):
                    return jsonify({
                        'error': (
                            'Cannot remove the last administrator'
                        ),
                    }), 400

                # Apply the changes.
                if new_active is not None:
                    user.active = new_active

                if 'displayName' in data:
                    user.display_name = (
                        data.get('displayName') or ''
                    ).strip()

                if new_groups is not None:
                    for name in KNOWN_GROUPS:
                        if name in new_groups:
                            add_user_to_group(
                                session,
                                user,
                                name,
                                created_by=actor,
                                timestamp=now,
                            )
                        else:
                            remove_user_from_group(session, user, name)

                user.updatedAt = now
                user.updatedBy = actor
                session.flush()
                return jsonify({
                    'message': 'User updated',
                    'user': user_to_dict(user, session),
                })
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    def delete_user(user_id):
        try:
            with get_database().session_scope() as session:
                user = session.get(User, user_id)
                if user is None:
                    return jsonify({'error': 'User not found'}), 404

                # Refuse to remove the last administrator: the
                # deployment would be left with nobody able to manage
                # users or content.
                if not _has_other_admin(session, user):
                    return jsonify({
                        'error': (
                            'Cannot remove the last administrator'
                        ),
                    }), 400

                session.delete(user)
                return jsonify({
                    'message': 'User removed',
                    'email': user.email,
                })
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/backup', methods=['GET'])
    def backup_database():
        try:
            with get_database().session_scope() as session:
                entries = [
                    entry_to_dict(entry)
                    for entry in session.query(Entry)
                    .order_by(Entry.id.asc())
                    .all()
                ]
                tags = [
                    tag_to_dict(tag)
                    for tag in session.query(Tag)
                    .order_by(Tag.id.asc())
                    .all()
                ]
                entry_tags = [
                    {
                        'entry_id': item.entry_id,
                        'tag_id': item.tag_id,
                    }
                    for item in session.query(EntryTag)
                    .order_by(EntryTag.entry_id.asc(), EntryTag.tag_id.asc())
                    .all()
                ]
                entry_links = [
                    {
                        'id': item.id,
                        'source_entry_id': item.source_entry_id,
                        'target_entry_id': item.target_entry_id,
                        'link_type': item.link_type,
                        'createdAt': item.createdAt,
                    }
                    for item in session.query(EntryLink)
                    .order_by(EntryLink.id.asc())
                    .all()
                ]
                entry_definitions = [
                    {
                        'id': item.id,
                        'entry_id': item.entry_id,
                        'tag_id': item.tag_id,
                        'definition': item.definition,
                        'createdAt': item.createdAt,
                        'updatedAt': item.updatedAt,
                    }
                    for item in session.query(EntryDefinition)
                    .order_by(EntryDefinition.id.asc())
                    .all()
                ]
                change_history = [
                    {
                        'id': item.id,
                        'timestamp': item.timestamp,
                        'action': item.action,
                        'term': item.term,
                        'oldData': item.oldData,
                        'newData': item.newData,
                        'discussion': item.discussion,
                        'user': item.user,
                    }
                    for item in session.query(ChangeHistory)
                    .order_by(ChangeHistory.id.asc())
                    .all()
                ]

                return jsonify(
                    {
                        'version': 2,
                        'exportedAt': utcnow_iso(),
                        'entries': entries,
                        'tags': tags,
                        'entry_tags': entry_tags,
                        'entry_links': entry_links,
                        'entry_definitions': entry_definitions,
                        'change_history': change_history,
                    }
                )
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/restore', methods=['POST'])
    def restore_database():
        try:
            data = optional_json_body()
            if not data or 'entries' not in data:
                return jsonify({'error': 'Invalid backup format'}), 400

            with get_database().session_scope() as session:
                session.query(EntryDefinition).delete(
                    synchronize_session=False
                )
                session.query(EntryTag).delete(synchronize_session=False)
                session.query(EntryLink).delete(synchronize_session=False)
                session.query(ChangeHistory).delete(
                    synchronize_session=False
                )
                session.query(Entry).delete(synchronize_session=False)
                session.query(Tag).delete(synchronize_session=False)
                session.flush()

                entry_id_map = {}
                tag_id_map = {}

                for tag in data.get('tags', []):
                    restored_tag = Tag(
                        name=tag['name'],
                        color=tag.get('color', '#004C8E'),
                        createdAt=tag.get('createdAt', utcnow_iso()),
                    )
                    session.add(restored_tag)
                    session.flush()
                    tag_id_map[tag['id']] = restored_tag.id

                for entry in data.get('entries', []):
                    restored_entry = Entry(
                        term=entry['term'],
                        definition=entry.get('definition', ''),
                        abbreviation=entry.get('abbreviation', ''),
                        dataType=entry.get('dataType', ''),
                        inputFormat=entry.get('inputFormat', ''),
                        variations=entry.get('variations', ''),
                        owner=entry.get('owner', ''),
                        stewards=entry.get('stewards', ''),
                        classification=normalize_classification(
                            entry.get('classification', 'public')
                        ),
                        discussion=entry.get('discussion', ''),
                        ddId=entry.get('ddId', ''),
                        createdAt=entry.get('createdAt', utcnow_iso()),
                        updatedAt=entry.get('updatedAt', utcnow_iso()),
                    )
                    session.add(restored_entry)
                    session.flush()
                    entry_id_map[entry['id']] = restored_entry.id

                for association in data.get('entry_tags', []):
                    new_entry_id = entry_id_map.get(
                        association['entry_id']
                    )
                    new_tag_id = tag_id_map.get(association['tag_id'])
                    if new_entry_id and new_tag_id:
                        existing_link = session.get(
                            EntryTag,
                            {
                                'entry_id': new_entry_id,
                                'tag_id': new_tag_id,
                            },
                        )
                        if not existing_link:
                            session.add(
                                EntryTag(
                                    entry_id=new_entry_id,
                                    tag_id=new_tag_id,
                                )
                            )

                for link in data.get('entry_links', []):
                    new_source = entry_id_map.get(link['source_entry_id'])
                    new_target = entry_id_map.get(link['target_entry_id'])
                    if new_source and new_target:
                        session.add(
                            EntryLink(
                                source_entry_id=new_source,
                                target_entry_id=new_target,
                                link_type=link.get('link_type', 'see_also'),
                                createdAt=link.get(
                                    'createdAt',
                                    utcnow_iso(),
                                ),
                            )
                        )

                for definition in data.get('entry_definitions', []):
                    new_entry_id = entry_id_map.get(definition['entry_id'])
                    new_tag_id = tag_id_map.get(definition['tag_id'])
                    if new_entry_id and new_tag_id:
                        session.add(
                            EntryDefinition(
                                entry_id=new_entry_id,
                                tag_id=new_tag_id,
                                definition=definition['definition'],
                                createdAt=definition.get(
                                    'createdAt',
                                    utcnow_iso(),
                                ),
                                updatedAt=definition.get(
                                    'updatedAt',
                                    utcnow_iso(),
                                ),
                            )
                        )

                for item in data.get('change_history', []):
                    session.add(
                        ChangeHistory(
                            timestamp=item['timestamp'],
                            action=item['action'],
                            term=item['term'],
                            oldData=json_string(item.get('oldData')),
                            newData=json_string(item.get('newData')),
                            discussion=item.get('discussion', ''),
                            user=current_user(),
                        )
                    )

                return jsonify(
                    {
                        'message': 'Restore completed successfully',
                        'entries': len(data.get('entries', [])),
                        'tags': len(data.get('tags', [])),
                        'entry_definitions': len(
                            data.get('entry_definitions', [])
                        ),
                        'entry_links': len(data.get('entry_links', [])),
                        'change_history': len(
                            data.get('change_history', [])
                        ),
                    }
                ), 200
        except SQLAlchemyError as exc:
            return jsonify({'error': str(exc)}), 500

    # ------------------------------------------------------------------
    # Front-end (SPA) static-file serving
    # ------------------------------------------------------------------
    # Static assets are served from an explicit allow-list rather than
    # from the filesystem root. Flask's built-in static handler maps
    # any URL straight onto a file path, which would otherwise expose
    # the SQLite database, the Python sources, and the .git directory
    # to anyone who can reach the port.
    @app.route('/admin', methods=['GET'])
    @app.route('/admin/', methods=['GET'])
    @app.route('/admin/<path:subpath>', methods=['GET'])
    def admin_shell(subpath=''):
        # Only serve the shell for the bare /admin path or non-file paths.
        # Requests for real admin assets (admin-api.js, admin.js) are
        # served by the allow-listed asset handler; anything else is a
        # 404 rather than the shell, so a missing asset is not masked.
        if subpath and '.' in subpath.split('/')[-1]:
            if f'admin/{subpath}' in STATIC_ASSETS:
                return serve_static_asset(f'admin/{subpath}')
            return not_found_response()
        return serve_static_asset('admin/index.html')

    @app.route('/<path:filename>', methods=['GET'])
    def static_asset(filename):
        # The API namespace is handled by its own routes and the API
        # 404 handler; never answer an /api/* path with the shell.
        if filename == 'api' or filename.startswith('api/'):
            return not_found_response()

        # Dotfiles (/.git/config, /.env) are never application routes.
        if any(part.startswith('.') for part in filename.split('/')):
            return not_found_response()

        # A request for a specific file is either an allow-listed
        # asset or a 404. It must never fall through to the SPA
        # shell, otherwise a path like /Dockerfile would return the
        # public page with a 200 and look like it succeeded.
        #
        # A path is treated as a file request when it has an
        # extension, names a directory, or matches a real file in the
        # project tree (some project files have no extension).
        if (
            '.' in filename
            or '/' in filename
            or _looks_like_project_file(filename)
        ):
            if filename in STATIC_ASSETS:
                return serve_static_asset(filename)
            # A nested path whose last segment is not a file (no
            # extension) is an application route, not a missing file.
            if (
                '/' in filename
                and '.' not in filename.rsplit('/', 1)[-1]
                and not _looks_like_project_file(filename)
            ):
                return current_app.send_static_file('index.html')
            return not_found_response()
        # A bare path with no extension is an application route, so
        # the SPA shell is the right answer.
        return current_app.send_static_file('index.html')

    @app.route('/', methods=['GET'])
    def index():
        return serve_static_asset('index.html')

    @app.errorhandler(404)
    def spa_fallback(error):
        # Don't intercept /api/* — those are real 404s.
        if request.path.startswith('/api/'):
            return not_found_response()

        # Dotfiles (/.git/config, /.env) are never application routes.
        if any(part.startswith('.') for part in request.path.split('/')):
            return not_found_response()

        # A path whose last segment looks like a file is a genuine
        # 404: serving the HTML shell there would mask a missing
        # asset behind a 200.
        last_segment = request.path.rsplit('/', 1)[-1]
        if '.' in last_segment:
            return not_found_response()

        # Everything else is an application route: return the public
        # shell so client-side routing keeps working.
        return current_app.send_static_file('index.html')
