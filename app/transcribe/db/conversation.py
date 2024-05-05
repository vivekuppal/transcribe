from typing import Optional
from datetime import datetime
import sqlalchemy as sqldb
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import text
from sqlalchemy.orm import Session, mapped_column
from sqlalchemy import Engine, insert
from db import AppDBBase

TABLE_NAME = 'Conversations'


class Conversation(AppDBBase):
    """One row in the Conversations Table"""
    __tablename__ = TABLE_NAME

    Id = mapped_column(Integer, primary_key=True)
    InvocationId = mapped_column(Integer, nullable=False)
    SpokenTime = mapped_column(DateTime, nullable=False)
    Speaker = mapped_column(String(40), nullable=False)
    Text = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"Invocation(id={self.id!r}, StartTime={self.StartTime!r}, EndTime={self.EndTime!r})"


class Conversations:
    """Represents the table Conversations in DB
    """
    _table_name = TABLE_NAME
    _db_table = None

    def __init__(self, engine, connection, commit: bool = True):
        # Create table if it does not exist in DB
        try:
            metadata = sqldb.MetaData()
            self._db_table = sqldb.Table(self._table_name, metadata, autoload_with=engine)
        except sqldb.exc.NoSuchTableError:
            # If table does not exist, create the table
            self._db_table = None
            print(f'Table: {self._table_name} does not exist. Creating table.')
            self.create_table(engine, metadata)

        self.populate_data()
        if commit:
            connection.commit()

    def create_table(self, engine: Engine, metadata):
        self._db_table = sqldb.Table(self._table_name, metadata,
                                     Column('Id', Integer(), sqldb.Identity(start=1), primary_key=True),
                                     Column("InvocationId", Integer, nullable=False),
                                     Column('SpokenTime', sqldb.Integer(), nullable=False),
                                     Column('Speaker', String(40), nullable=False),
                                     Column('Text', String, nullable=False),
                                     )

        metadata.create_all(engine)

    def insert_conversations(self, engine: Engine):
        # InvocationId is the current invocation
        # Time, Speaker, Text has to be extracted from the conversation

        # Get current invocation id
        meta = sqldb.MetaData()
        meta.reflect(engine)
        convo_table = meta.tables['Conversations']

        inv_id = 6

        data = [(inv_id, datetime.utcnow(), 'You', 'Text 1'),
                (inv_id, datetime.utcnow(), 'You', 'Text 2'),
                (inv_id, datetime.utcnow(), 'You', 'Text 3'),
                (inv_id, datetime.utcnow(), 'You', 'Text 4'),
                (inv_id, datetime.utcnow(), 'You', 'Text 5'),
                (inv_id, datetime.utcnow(), 'You', 'Text 6'),
                (inv_id, datetime.utcnow(), 'You', 'Text 7'),
                (inv_id, datetime.utcnow(), 'You', 'Text 8'),
                (inv_id, datetime.utcnow(), 'You', 'Text 9')]

        stmt = insert(convo_table).values([{
            'InvocationId': inv_id,
            'SpokenTime': stime,
            'Speaker': speaker,
            'Text': text} for inv_id, stime, speaker, text in data])

        with Session(engine) as session:
            session.execute(stmt)
            session.commit()
            session.close()

    def populate_data(self):
        pass
