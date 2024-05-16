from typing import Optional
from datetime import datetime
import sqlalchemy as sqldb
from sqlalchemy.sql import text
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy import Engine
# from db import AppDBBase

TABLE_NAME = 'ApplicationInvocations'


class Invocation():
    """One row in the ApplicationInvocations Table
    """
    __tablename__ = TABLE_NAME

    Id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    StartTime: Mapped[datetime]
    EndTime: Mapped[Optional[datetime]]

    def __repr__(self) -> str:
        return f"Invocation(id={self.Id!r}, StartTime={self.StartTime!r}, EndTime={self.EndTime!r})"


class ApplicationInvocations:
    """Represents the table ApplicationInvocations in DB
    """
    _table_name = TABLE_NAME
    _db_table = None
    _invocation_id: int = None

    def __init__(self, engine):
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

    def create_table(self, engine, metadata):
        """Create invocation table.
        """
        self._db_table = sqldb.Table(self._table_name, metadata,
                                     sqldb.Column('Id', sqldb.Integer(), sqldb.Identity(start=1), primary_key=True, ),
                                     sqldb.Column('StartTime', sqldb.Integer(), nullable=False, default=datetime.utcnow),
                                     sqldb.Column('EndTime', sqldb.Integer(), nullable=True))

        metadata.create_all(engine)

    def insert_start_time(self, engine: Engine):
        """Set the time application was started.
        """
        try:
            query = text(f'INSERT INTO {self._table_name} (StartTime) VALUES("{datetime.utcnow()}")')
            with Session(engine) as session:
                result = session.execute(query)
                self._invocation_id = result.lastrowid
                session.commit()
                session.close()
        except Exception as ex:
            print(ex)

    def populate_end_time(self, engine):
        """Set the time application was shutdown
        """
        with Session(engine) as session:
            row_id = self.get_invocation_id()
            query = text(f'UPDATE {self._table_name} Set EndTime ="{datetime.utcnow()}" where Id = {row_id}')
            session.execute(query)
            session.commit()
            session.close()

    def get_invocation_id(self) -> int:
        """Get the invocation id of this instance of the application.
           This id is constant for a specific run of the application.
        """
        return self._invocation_id

    def populate_data(self):
        pass
