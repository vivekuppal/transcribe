"""
This module defines classes and methods for managing application invocation records
in a SQLAlchemy database. The `Invocation` class represents a single invocation record,
while the `ApplicationInvocations` class provides methods to interact with the database
table, including creating the table, inserting start times, and updating end times.
"""

from typing import Optional
from datetime import datetime
import sqlalchemy as sqldb
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy import Engine
from sqlalchemy.orm import declarative_base

# from db import AppDBBase

TABLE_NAME = 'ApplicationInvocations'


class Invocation(declarative_base()):
    """
    Represents a row in the ApplicationInvocations table.

    Attributes:
        Id (int): The primary key of the table, auto-incremented.
        StartTime (datetime): The start time of the application invocation.
        EndTime (Optional[datetime]): The end time of the application invocation.
    """
    __tablename__ = TABLE_NAME

    Id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    StartTime: Mapped[datetime]
    EndTime: Mapped[Optional[datetime]]

    def __repr__(self) -> str:
        """
        Returns a string representation of the Invocation instance.

        Returns:
            str: A string representing the Invocation instance.
        """
        return f"Invocation(id={self.Id!r}, StartTime={self.StartTime!r}, EndTime={self.EndTime!r})"


class ApplicationInvocations:
    """
    Manages the ApplicationInvocations table in the database.

    Provides methods to create the table, insert start times, update end times, 
    and retrieve the current invocation ID.

    Attributes:
        _table_name (str): The name of the table.
        _db_table (Optional[sqldb.Table]): The SQLAlchemy Table object.
        _invocation_id (Optional[int]): The ID of the current invocation.
    """
    _table_name = TABLE_NAME
    _db_table = None
    _invocation_id: int = None

    def __init__(self, engine):
        """
        Initializes the ApplicationInvocations instance.

        If the table does not exist in the database, it creates the table.

        Args:
            engine (Engine): The SQLAlchemy engine to connect to the database.
        """
        try:
            metadata = sqldb.MetaData()
            self._db_table = sqldb.Table(self._table_name, metadata, autoload_with=engine)
        except sqldb.exc.NoSuchTableError:
            # If table does not exist, create the table
            self._db_table = None
            print(f'Table: {self._table_name} does not exist. Creating table.')
            self.create_table(engine, metadata)

        self.populate_data()

    def create_table(self, engine, metadata):
        """
        Creates the ApplicationInvocations table in the database.

        Args:
            engine (Engine): The SQLAlchemy engine to connect to the database.
            metadata (MetaData): The SQLAlchemy MetaData object.
        """
        self._db_table = sqldb.Table(self._table_name, metadata,
                                     sqldb.Column('Id', sqldb.Integer(), sqldb.Identity(start=1), primary_key=True),
                                     sqldb.Column('StartTime', sqldb.DateTime(), nullable=False,
                                                  default=datetime.utcnow),
                                     sqldb.Column('EndTime', sqldb.DateTime(), nullable=True))

        metadata.create_all(engine)

    def insert_start_time(self, engine: Engine):
        """
        Inserts the start time of the application invocation into the database.

        Args:
            engine (Engine): The SQLAlchemy engine to connect to the database.

        Raises:
            Exception: If there is an error during insertion.
        """
        try:
            with Session(engine) as session:
                new_invocation = Invocation(StartTime=datetime.utcnow())
                session.add(new_invocation)
                session.commit()
                self._invocation_id = new_invocation.Id
        except Exception as ex:
            print(f'Failed to insert start time: {ex}')

    def populate_end_time(self, engine: Engine):
        """
        Updates the end time of the current application invocation in the database.

        Args:
            engine (Engine): The SQLAlchemy engine to connect to the database.

        Raises:
            Exception: If there is an error during the update.
        """
        if self._invocation_id is None:
            print('Invocation ID is not set. Cannot update end time.')
            return

        try:
            with Session(engine) as session:
                invocation = session.query(Invocation).get(self._invocation_id)
                if invocation:
                    invocation.EndTime = datetime.utcnow()
                    session.commit()
        except Exception as ex:
            print(f'Failed to update end time: {ex}')

    def get_invocation_id(self) -> int:
        """
        Retrieves the invocation ID of the current application instance.

        Returns:
            int: The invocation ID.
        """
        return self._invocation_id

    def populate_data(self):
        """
        Placeholder method for populating the table with initial data.
        """
        pass
