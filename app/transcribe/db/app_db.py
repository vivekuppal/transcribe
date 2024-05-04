import sys
import db.app_invocations as appi
import logging
import sqlalchemy as db
from sqlalchemy import Engine, Connection
sys.path.append('../..')
from tsutils import Singleton  # noqa: E402 pylint: disable=C0413

# TO DO
# Add another table to DB


class AppDB(Singleton.Singleton):
    _tables = [
        'ApplicationInvocations'
    ]
    _app_base_folder: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_db(self, app_base_folder):
        self._app_base_folder = app_base_folder
        # Create DB file if it does not exist
        # C:\....\transcribe\app\transcribe
        engine = db.create_engine(f'sqlite:///{self._app_base_folder}/logs/app.db')
        connection = engine.connect()

        # Initialize DB logger
        db_log_file_name = f'{self._app_base_folder}/logs/db.log'
        db_handler = logging.FileHandler(db_log_file_name)
        db_logger = logging.getLogger('sqlalchemy')
        db_handler_log_level = logging.INFO
        db_logger_log_level = logging.DEBUG
        db_handler.setLevel(db_handler_log_level)
        db_logger.addHandler(db_handler)
        db_logger.setLevel(db_logger_log_level)

        # Initialize all the tables
        appi.ApplicationInvocations(engine=engine, connection=connection, commit=False)
        connection.commit()
        connection.close()

    def initialize_app(self):
        engine: Engine = db.create_engine(f'sqlite:///{self._app_base_folder}/logs/app.db')
        connection: Connection = engine.connect()
        appi.ApplicationInvocations(engine, connection).insert_start_time(engine=engine)

    def shutdown_app(self):
        engine = db.create_engine(f'sqlite:///{self._app_base_folder}/logs/app.db')
        connection = engine.connect()
        appi.ApplicationInvocations(engine=engine, connection=connection, commit=False).populate_end_time(engine)
