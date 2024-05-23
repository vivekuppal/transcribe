import sys
import logging
import sqlalchemy as sqldb
from sqlalchemy import Engine
import db.app_invocations as appi
from db import conversation as convo
from db import llm_responses as lresp
from db import summaries as s
sys.path.append('../..')
from tsutils import Singleton  # noqa: E402 pylint: disable=C0413

# TO DO
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
    # Dictionary of Table name to Table objects
    # Table objects are populated in InitializeDB method.
    # No other class should instantiate any of the table objects, rather use the
    # objects from AppDB class.
    _tables = {
        appi.TABLE_NAME: None,
        convo.TABLE_NAME: None,
        lresp.TABLE_NAME: None,
        s.TABLE_NAME: None
    }

    # db_file_path
    # current_working_dir
    # db_log_file
    _db_context: dict = None
    _engine: Engine = None
    _db_logger: logging.Logger = None

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
        self._engine = sqldb.create_engine(f'sqlite:///{db_file_path}')
        connection = self._engine.connect()

        # Initialize DB logger
        db_log_file_name = f'{self._db_context["db_log_file"]}'
        db_handler = logging.FileHandler(db_log_file_name, encoding='utf-8')
        self._db_logger = logging.getLogger('sqlalchemy')
        db_handler_log_level = logging.INFO
        db_logger_log_level = logging.DEBUG
        db_handler.setLevel(db_handler_log_level)
        self._db_logger.addHandler(db_handler)
        self._db_logger.setLevel(db_logger_log_level)

        # Initialize all the tables
        self._tables[appi.TABLE_NAME] = appi.ApplicationInvocations(engine=self._engine)
        self._tables[convo.TABLE_NAME] = convo.Conversations(engine=self._engine)
        self._tables[lresp.TABLE_NAME] = lresp.LLMResponses(engine=self._engine)
        self._tables[s.TABLE_NAME] = s.Summaries(engine=self._engine)
        connection.commit()
        connection.close()

    def get_logger(self) -> logging.Logger:
        """Get DB logger
        """
        return self._db_logger

    def get_context(self) -> dict:
        """Get DB context
        """
        return self._db_context

    def initialize_app(self):
        """Application initialization
        """
        engine: Engine = sqldb.create_engine(f'sqlite:///{self._db_context["db_file_path"]}')
        # Insert any necessary data in tables
        self._tables[appi.TABLE_NAME].insert_start_time(engine=engine)

    def get_invocation_id(self) -> int:
        """Get the invocation id for this invocation of the application.
        """
        return self._tables[appi.TABLE_NAME].get_invocation_id()

    def get_engine(self) -> Engine:
        """Get DB Engine object
        """
        return self._engine

    def get_object(self, name):
        """Get corresponding table object
        """
        return self._tables[name]

    def shutdown_app(self):
        """Application shutdown
        """
        engine = sqldb.create_engine(f'sqlite:///{self._db_context["db_file_path"]}')
        self._tables[appi.TABLE_NAME].populate_end_time(engine)
