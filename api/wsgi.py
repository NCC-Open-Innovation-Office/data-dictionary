import os

from sqlalchemy.engine import make_url

try:
    from api.app import create_app
except ImportError:
    from app import create_app


app = create_app()


if __name__ == '__main__':
    database = app.extensions['dd_db']
    parsed_url = make_url(database.database_url)
    if parsed_url.drivername.startswith('mssql'):
        app.logger.info('Starting API with MSSQL backend')
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)