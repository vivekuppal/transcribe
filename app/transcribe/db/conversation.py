import sqlalchemy as sqldb
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import text
from sqlalchemy.orm import Session, mapped_column
from sqlalchemy import Engine, insert

TABLE_NAME = 'Conversations'


class Conversation():
    """One row in the Conversations Table"""
    __tablename__ = TABLE_NAME

    Id = mapped_column(Integer, primary_key=True, autoincrement=True)
    InvocationId = mapped_column(Integer, nullable=False)
    SpokenTime = mapped_column(DateTime, nullable=False)
    Speaker = mapped_column(String(40), nullable=False)
    Text = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"Invocation(id={self.Id!r}, SpokenTime={self.SpokenTime!r}," \
               f"Speaker={self.Speaker!r}, Text={self.Text!r})"


class Conversations:
    """Represents the table Conversations in DB
    """
    _table_name = TABLE_NAME
    _db_table = None

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

    def create_table(self, engine: Engine, metadata):
        """Create conversation table in DB.
        """
        self._db_table = sqldb.Table(self._table_name, metadata,
                                     Column('Id', Integer(), sqldb.Identity(start=1),
                                            primary_key=True),
                                     Column("InvocationId", Integer, nullable=False),
                                     Column('SpokenTime', sqldb.Integer(), nullable=False),
                                     Column('Speaker', String(40), nullable=False),
                                     Column('Text', String, nullable=False),
                                     )

        metadata.create_all(engine)

    def insert_conversation(self, invocation_id, spoken_time, speaker_name, convo_text, engine):
        """Insert a conversation entry
        """
        stmt = insert(self._db_table).values([{
            'InvocationId': invocation_id,
            'SpokenTime': spoken_time,
            'Speaker': speaker_name,
            'Text': convo_text}])

        with Session(engine) as session:
            session.execute(stmt)
            session.commit()
            session.close()

    def update_conversation(self, invocation_id, convo_text, engine):
        """Insert a conversation entry
        """
        # print('DB Update conversation')
        try:
            with Session(engine) as session:
                # Get row id we need to update
                query = text(f'SELECT MAX(Id) '
                             f'FROM Conversations '
                             f'WHERE InvocationId = {invocation_id}')
                result = session.execute(query)
                rows = result.fetchall()
                convo_id = rows[0][0]

                if convo_id is None:
                    return

                # Update the row
                query = text(f'UPDATE Conversations '
                             f'SET Text = "{convo_text}" '
                             f'WHERE Id = {convo_id}')
                session.execute(query)
                session.commit()
                session.close()
        except Exception as ex:
            print(ex)

    def populate_data(self):
        """Not Implemented
        """
        pass   # pylint: disable=W0107
