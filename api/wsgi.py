import logging
import os
import sys

from sqlalchemy.engine import make_url

try:
    from api.app import create_app
except ImportError:
    from app import create_app


app = create_app()


if __name__ == '__main__':
    if not app.config['TESTING']:
        # Clear default handlers to avoid duplicate logs
        app.logger.handlers = []

        # Create a stream handler targeting stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        # Define a clean log format
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        #handler.setFormatter(formatter)

        # Add handler to Flask's logger
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)

    database = app.extensions['dd_db']
    parsed_url = make_url(database.database_url)
    if parsed_url.drivername.startswith('mssql'):
        app.logger.info('Starting API with MSSQL backend')
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
