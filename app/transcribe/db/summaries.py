"""
This module defines classes and methods for managing summary records
in a SQLAlchemy database. The `Summary` class represents a single summary record,
while the `Summaries` class provides methods to interact with the database table,
including creating the table, inserting summaries, and populating initial data.
"""

import datetime
import sqlalchemy as sqldb
from sqlalchemy import Column, Integer, String, MetaData, DateTime
from sqlalchemy.orm import Session, mapped_column, declarative_base, Mapped
from sqlalchemy import Engine, insert

TABLE_NAME = 'Summaries'


class Summary(declarative_base()):
    """
    Represents a row in the Summaries table.

    Attributes:
        Id (int): The primary key of the table, auto-incremented.
        CreatedTime (datetime): The time the summary was created.
        InvocationId (int): The ID of the related invocation.
        ConversationId (int): The ID of the related conversation.
        Text (str): The content of the summary.
    """
    __tablename__ = TABLE_NAME

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CreatedTime: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False,
                                                           default=datetime.datetime.utcnow)
    InvocationId: Mapped[int] = mapped_column(Integer, nullable=False)
    ConversationId: Mapped[int] = mapped_column(Integer, nullable=False)
    Text: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        """
        Returns a string representation of the Summary instance.

        Returns:
            str: A string representing the Summary instance.
        """
        return (f"Summary(Id={self.Id!r}, CreatedTime={self.CreatedTime!r}, "
                f"InvocationId={self.InvocationId!r}, ConversationId={self.ConversationId!r}, "
                f"Text={self.Text!r})")


class Summaries:
    """
    Manages the Summaries table in the database.

    Provides methods to create the table, insert summaries, and populate initial data.

    Attributes:
        _table_name (str): The name of the table.
        _db_table (Optional[sqldb.Table]): The SQLAlchemy Table object.
        _metadata (MetaData): The SQLAlchemy MetaData object.
    """
    _table_name = TABLE_NAME
    _db_table = None
    _metadata: MetaData = None

    def __init__(self, engine: Engine):
        """
        Initializes the Summaries instance.

        If the table does not exist in the database, it creates the table.

        Args:
            engine (Engine): The SQLAlchemy engine to connect to the database.
        """
        self.engine = engine
        self.metadata = sqldb.MetaData()
        self._initialize_table()

    def _initialize_table(self):
        """Initializes the Summaries table."""
        try:
            self._db_table = sqldb.Table(self._table_name, self.metadata, autoload_with=self.engine)
        except sqldb.exc.NoSuchTableError:
            self._db_table = None
            print(f'Table: {self._table_name} does not exist. Creating table.')
            self.create_table()

        self.populate_data()

    def create_table(self):
        """
        Creates the Summaries table in the database.
        """
        self._db_table = sqldb.Table(
            self._table_name, self.metadata,
            Column('Id', Integer, sqldb.Identity(start=1), primary_key=True),
            Column('CreatedTime', DateTime, nullable=False, default=datetime.datetime.utcnow),
            Column('InvocationId', Integer, nullable=False),
            Column('ConversationId', Integer, nullable=False),
            Column('Text', String, nullable=False)
        )

        self.metadata.create_all(self.engine)

    def insert_summary(self, invocation_id: int, conversation_id: int, text: str) -> int:
        """
        Inserts a summary entry into the Summaries table.

        Args:
            invocation_id (int): The ID of the related invocation.
            conversation_id (int): The ID of the related conversation.
            text (str): The content of the summary.

        Returns:
            int: The ID of the inserted summary entry.
        """
        stmt = insert(self._db_table).values({
            'InvocationId': invocation_id,
            'ConversationId': conversation_id,
            'Text': text,
            'CreatedTime': datetime.datetime.utcnow()
        })

        with Session(self.engine) as session:
            result = session.execute(stmt)
            session.commit()

        return result.lastrowid

    def populate_data(self):
        """
        Placeholder method for populating the table with initial data.
        """
        pass
