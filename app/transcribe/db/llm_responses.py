"""
This module defines classes and methods for managing LLM response records
in a SQLAlchemy database. The `LLMResponse` class represents a single response record,
while the `LLMResponses` class provides methods to interact with the database table,
including creating the table, inserting responses, and populating initial data.
"""

import datetime
import sqlalchemy as sqldb
from sqlalchemy import Column, Integer, String, MetaData, DateTime, Engine, insert, select
from sqlalchemy.orm import Session, mapped_column, declarative_base, Mapped

TABLE_NAME = 'LLMResponses'


class LLMResponse(declarative_base()):
    """
    Represents a row in the LLMResponses table.

    Attributes:
        Id (int): The primary key of the table, auto-incremented.
        CreatedTime (datetime): The time the response was created.
        InvocationId (int): The ID of the related invocation.
        ConversationId (int): The ID of the related conversation.
        Text (str): The content of the response.
    """
    __tablename__ = TABLE_NAME

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CreatedTime: Mapped[datetime.datetime] = mapped_column(DateTime,
                                                           nullable=False,
                                                           default=datetime.datetime.utcnow)
    InvocationId: Mapped[int] = mapped_column(Integer, nullable=False)
    ConversationId: Mapped[int] = mapped_column(Integer, nullable=False)
    Text: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        """
        Returns a string representation of the LLMResponse instance.

        Returns:
            str: A string representing the LLMResponse instance.
        """
        return (f"LLMResponse(Id={self.Id!r}, CreatedTime={self.CreatedTime!r}, "
                f"InvocationId={self.InvocationId!r}, ConversationId={self.ConversationId!r}, "
                f"Text={self.Text!r})")


class LLMResponses:
    """
    Manages the LLMResponses table in the database.

    Provides methods to create the table, insert responses, and populate initial data.

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
        Initializes the LLMResponses instance.

        If the table does not exist in the database, it creates the table.

        Args:
            engine (Engine): The SQLAlchemy engine to connect to the database.
        """
        self.engine = engine
        self._metadata = sqldb.MetaData()
        self._initialize_table()

    def _initialize_table(self):
        """Initializes the LLMResponses table."""
        try:
            self._db_table = sqldb.Table(self._table_name, self._metadata, autoload_with=self.engine)
        except sqldb.exc.NoSuchTableError:
            self._db_table = None
            print(f'Table: {self._table_name} does not exist. Creating table.')
            self.create_table()

        self.populate_data()

    def create_table(self):
        """
        Creates the LLMResponses table in the database.
        """
        self._db_table = sqldb.Table(
            self._table_name, self._metadata,
            Column('Id', Integer, sqldb.Identity(start=1), primary_key=True),
            Column('CreatedTime', DateTime, nullable=False, default=datetime.datetime.utcnow),
            Column('InvocationId', Integer, nullable=False),
            Column('ConversationId', Integer, nullable=False),
            Column('Text', String, nullable=False)
        )

        self._metadata.create_all(self.engine)

    def insert_response(self, invocation_id: int, conversation_id: int, text: str) -> int:
        """
        Inserts a response entry into the LLMResponses table.

        Args:
            invocation_id (int): The ID of the related invocation.
            conversation_id (int): The ID of the related conversation.
            text (str): The content of the response.

        Returns:
            int: The ID of the inserted response entry.
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

        return result.inserted_primary_key[0]

    def get_text_by_invocation_and_conversation(self, invocation_id: int, conversation_id: int) -> str:
        """
        Retrieves the text of a response based on the invocation_id and conversation_id.

        Args:
            invocation_id (int): The ID of the related invocation.
            conversation_id (int): The ID of the related conversation.

        Returns:
            str: The text of the matching response or None if no match is found.
        """
        stmt = select(self._db_table.c.Text).where(
            self._db_table.c.InvocationId == invocation_id,
            self._db_table.c.ConversationId == conversation_id
        )

        with Session(self.engine) as session:
            result = session.execute(stmt).scalar()

        return result

    def populate_data(self):
        """
        Placeholder method for populating the table with initial data.
        """
        pass
