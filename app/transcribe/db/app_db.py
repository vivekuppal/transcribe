import sys
import db.app_invocations as appi
from db import conversation
import logging
import sqlalchemy as db
from sqlalchemy import Engine
from sqlalchemy.orm import Session
sys.path.append('../..')
from tsutils import Singleton  # noqa: E402 pylint: disable=C0413

# TO DO
# Add another table to DB
# Create a common base class for tables may be
# Test with unicode to ensure that unicode strings can be saved in the conversation DB
# Handle the case of clearing the conversation


class DBInitException(Exception):
    pass


class AppDB(Singleton.Singleton):
    """Database associated with Transcribe.
    This class is implemented as a Singleton.
    Correct sequence of operations for initialization is
        adb = AppDB()
        adb.initialize_db(app_base_folder)
        adb.initialize_app()
    """
    # Dictionary of Table name to Table object values
    _tables = {
        'ApplicationInvocations': None,
        'Conversations': None
    }

    # db_file_path
    # current_working_dir
    # db_log_file
    _db_context: dict = None
    _engine: Engine = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_db(self, db_context: dict = None):
        """Initialize application DB.
        """
        if db_context is None and self._db_context is None:
            raise DBInitException('Need db context object to initialize the DB.')

        self._db_context = db_context
        # Create DB file if it does not exist
        # C:\....\transcribe\app\transcribe
        db_file_path = self._db_context["db_file_path"]
        self._engine = db.create_engine(f'sqlite:///{db_file_path}')
        connection = self._engine.connect()

        # Initialize DB logger
        db_log_file_name = f'{self._db_context["db_log_file"]}'
        db_handler = logging.FileHandler(db_log_file_name)
        db_logger = logging.getLogger('sqlalchemy')
        db_handler_log_level = logging.INFO
        db_logger_log_level = logging.DEBUG
        db_handler.setLevel(db_handler_log_level)
        db_logger.addHandler(db_handler)
        db_logger.setLevel(db_logger_log_level)

        # Initialize all the tables
        self._tables['ApplicationInvocations'] = appi.ApplicationInvocations(engine=self._engine,
                                                                             connection=connection,
                                                                             commit=False)
        self._tables['Conversations'] = conversation.Conversations(db_context,
                                                                   self._engine,
                                                                   commit=False)
        connection.commit()
        connection.close()

    def get_context(self) -> dict:
        """Get DB context
        """
        return self._db_context

    def initialize_app(self):
        """Application initialization
        """
        engine: Engine = db.create_engine(f'sqlite:///{self._db_context["db_file_path"]}')
        # Insert any necessary data in tables
        self._tables['ApplicationInvocations'].insert_start_time(engine=engine)

    def get_invocation_id(self) -> int:
        """Get the invocation id for this invocation of the application.
        """
        return self._tables['ApplicationInvocations'].get_invocation_id()

    def get_engine(self) -> Engine:
        return self._engine

    def get_object(self, name):
        return self._tables[name]

    def shutdown_app(self):
        """Application shutdown
        """
        engine = db.create_engine(f'sqlite:///{self._db_context["db_file_path"]}')
        # connection = engine.connect()
        self._tables['ApplicationInvocations'].populate_end_time(engine)
        # Get the list of tuples that encapsulate the conversation
        # data = []
        # conversation.Conversations(engine, connection).save_conversations(engine, data)
