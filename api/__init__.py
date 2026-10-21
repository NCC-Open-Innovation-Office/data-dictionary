"""Application package for the Data Dictionary API.

`create_app` and `application` are exposed lazily (PEP 562) so that
importing this package has no side effects.

Previously this module eagerly imported `api.wsgi`, whose module-level
`create_app()` call resolved the database from the DATABASE environment
variable and created/migrated it on disk. Importing `api.app` -- for
example from the test suite -- therefore wrote to whichever database
file the environment pointed at, and the eagerly created Flask instance
also shadowed the `api.app` submodule, so `api.app.create_app` raised
AttributeError.

Names
-----
create_app    Factory that builds a configured Flask application.
application   The module-level Flask application (from `api.wsgi`).

The `api.app` submodule is left unshadowed, so `from api.app import
create_app` keeps working as it always has.
"""

__all__ = ['application', 'create_app']


def __getattr__(name):
    if name == 'create_app':
        from api.app import create_app

        globals()['create_app'] = create_app
        return create_app

    if name == 'application':
        from api.wsgi import app

        globals()['application'] = app
        return app

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
