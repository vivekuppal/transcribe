from typing import Optional
import sqlalchemy as db
from sqlalchemy import func
from sqlalchemy.sql import text
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import Engine

TABLE_NAME = 'ApplicationInvocations'


class Base(DeclarativeBase):
    pass


class Invocation(Base):
    __tablename__ = TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True)
    StartTime: Mapped[datetime]
    EndTime: Mapped[Optional[datetime]]

    def __repr__(self) -> str:
        return f"Invocation(id={self.id!r}, StartTime={self.StartTime!r}, EndTime={self.EndTime!r})"


class ApplicationInvocations:
    """Represents the table ApplicationInvocations in DB
    """
    _table_name = TABLE_NAME
    _db_table = None

    def __init__(self, engine, connection, commit: bool = True):
        # Create table if it does not exist in DB
        try:
            metadata = db.MetaData()
            self._db_table = db.Table(self._table_name, metadata, autoload_with=engine)
        except db.exc.NoSuchTableError:
            # If table does not exist, create the table
            self._db_table = None
            print(f'Table: {self._table_name} does not exist. Creating table.')
            self.create_table(engine, metadata)

        self.populate_data(engine)
        if commit:
            connection.commit()

    def create_table(self, engine, metadata):
        self._db_table = db.Table(self._table_name, metadata,
                                  db.Column('Id', db.Integer(), db.Identity(start=1), primary_key=True, ),
                                  db.Column('StartTime', db.Integer(),
                                            nullable=False,
                                            default=datetime.utcnow),
                                  db.Column('EndTime', db.Integer(), nullable=True))

        metadata.create_all(engine)

    def insert_start_time(self, engine: Engine):
        try:
            query = text(f'INSERT INTO {self._table_name} (StartTime) VALUES("{datetime.utcnow()}")')
            with Session(engine) as session:
                session.execute(query)
                session.commit()
                session.close()
        except Exception as ex:
            print(ex)

    def populate_end_time(self, engine):
        with Session(engine) as session:
            row = session.query(Invocation.id, func.max(Invocation.id))
            result = row.all()
            # get the id from above query
            row_id = result[0][0]
            query = text(f'UPDATE {self._table_name} Set EndTime ="{datetime.utcnow()}" where id = {row_id}')
            session.execute(query)
            session.commit()
            session.close()

    def populate_data(engine, connection):
        pass
