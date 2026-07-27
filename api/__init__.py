try:
    from api.app import create_app
    from api.wsgi import app
except ImportError:
    from app import create_app
    from wsgi import app


__all__ = ['app', 'create_app']