"""
This module defines classes and methods for managing conversation records
in a SQLAlchemy database. The `Conversation` class represents a single conversation record,
while the `Conversations` class provides methods to interact with the database table,
including creating the table, inserting, updating, and retrieving conversations.
"""

from datetime import datetime
import sqlalchemy as sqldb
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import update, text
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy import Engine, insert
from sqlalchemy.orm import declarative_base

TABLE_NAME = 'Conversations'


class Conversation(declarative_base()):
    """
    Represents a row in the Conversations table.

    Attributes:
        Id (int): The primary key of the table, auto-incremented.
        InvocationId (int): The ID of the related invocation.
        SpokenTime (datetime): The time the conversation was spoken.
        Speaker (str): The name of the speaker.
        Text (str): The content of the conversation.
    """
    __tablename__ = TABLE_NAME

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    InvocationId: Mapped[int] = mapped_column(Integer, nullable=False)
    SpokenTime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Speaker: Mapped[str] = mapped_column(String(40), nullable=False)
    Text: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        """
        Returns a string representation of the Conversation instance.

        Returns:
            str: A string representing the Conversation instance.
        """
        return (f"Conversation(id={self.Id!r}, InvocationId={self.InvocationId!r}, "
                f"SpokenTime={self.SpokenTime!r}, Speaker={self.Speaker!r}, Text={self.Text!r})")


class Conversations:
    """
    Manages the Conversations table in the database.

    Provides methods to create the table, insert conversations, update conversations,
    and retrieve conversation IDs.

    Attributes:
        _table_name (str): The name of the table.
        _db_table (Optional[sqldb.Table]): The SQLAlchemy Table object.
    """
    _table_name = TABLE_NAME
    _db_table = None

    def __init__(self, engine: Engine):
        """
        Initializes the Conversations instance.

        If the table does not exist in the database, it creates the table.

        Args:
            engine (Engine): The SQLAlchemy engine to connect to the database.
        """
        self.engine = engine
        self.metadata = sqldb.MetaData()
        self._initialize_table()

    def _initialize_table(self):
        """Initializes the Conversations table."""
        try:
            self._db_table = sqldb.Table(self._table_name, self.metadata, autoload_with=self.engine)
        except sqldb.exc.NoSuchTableError:
            self._db_table = None
            print(f'Table: {self._table_name} does not exist. Creating table.')
            self.create_table()

        self.populate_data()

    def create_table(self):
        """
        Creates the Conversations table in the database.
        """
        self._db_table = sqldb.Table(
            self._table_name, self.metadata,
            Column('Id', Integer, sqldb.Identity(start=1), primary_key=True),
            Column("InvocationId", Integer, nullable=False),
            Column('SpokenTime', DateTime, nullable=False),
            Column('Speaker', String(40), nullable=False),
            Column('Text', String, nullable=False)
        )

        self.metadata.create_all(self.engine)

    def insert_conversation(self, invocation_id: int, spoken_time: datetime,
                            speaker_name: str, convo_text: str) -> int:
        """
        Inserts a conversation entry into the Conversations table.

        Args:
            invocation_id (int): The ID of the related invocation.
            spoken_time (datetime): The time the conversation was spoken.
            speaker_name (str): The name of the speaker.
            convo_text (str): The content of the conversation.

        Returns:
            int: The ID of the inserted conversation entry.
        """
        stmt = insert(self._db_table).values([
            {
                'InvocationId': invocation_id,
                'SpokenTime': spoken_time,
                'Speaker': speaker_name,
                'Text': convo_text
            }
        ])

        with Session(self.engine) as session:
            result = session.execute(stmt)
            session.commit()

        convo_id = result.lastrowid
        return convo_id

    def get_max_convo_id(self, speaker: str, inv_id: int) -> int:
        """
        Retrieves the ID of the last conversation row inserted in the database for a given speaker.

        Args:
            speaker (str): The name of the speaker.

        Returns:
            int: The ID of the last conversation entry for the given speaker.
        """
        stmt = text(f'SELECT MAX(Id) FROM {self._table_name} WHERE Speaker = :speaker and InvocationId = :inv_id')
        with Session(self.engine) as session:
            result = session.execute(stmt, {'speaker': speaker, 'inv_id': inv_id})
            convo_id = result.scalar()
            session.commit()

        return convo_id

    def get_convo_id_by_speaker_and_text(self, speaker: str, input_text: str, inv_id: int) -> int:
        """
        Retrieves the ID of the conversation row that matches the given speaker and text.

        Args:
            speaker (str): The name of the speaker.
            text (str): The content of the conversation.

        Returns:
            int: The ID of the matching conversation entry.
        """
        stmt = text(f'SELECT Id FROM {self._table_name} WHERE Speaker = :speaker and Text = :text and InvocationId = :inv_id')
        with Session(self.engine) as session:
            result = session.execute(stmt, {'speaker': speaker, 'text': input_text, 'inv_id': inv_id})
            convo_id = result.scalar()
            session.commit()

        return convo_id

    def update_conversation(self, conversation_id: int, convo_text: str):
        """
        Updates the text of a conversation entry in the Conversations table.

        Args:
            conversation_id (int): The ID of the conversation entry to update.
            convo_text (str): The new content of the conversation.

        Raises:
            ValueError: If the conversation_id is None.
        """
        if conversation_id is None:
            # This happens for system prompts, Needs investigation
            return

        try:
            with Session(self.engine) as session:
                stmt = update(self._db_table).where(self._db_table.c['Id'] == conversation_id).values(Text=convo_text)
                session.execute(stmt)
                session.commit()
        except Exception as ex:
            print(f'Failed to update conversation: {ex}')

    def populate_data(self):
        """Placeholder method for populating the table with initial data."""
        pass
