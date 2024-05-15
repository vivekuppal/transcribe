from datetime import datetime
import sqlalchemy as sqldb
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import text
from sqlalchemy.orm import Session, mapped_column
from sqlalchemy import Engine, insert
# from db import DB_CONTEXT

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
        return f"Invocation(id={self.Id!r}, SpokenTime={self.SpokenTime!r}, Speaker={self.Speaker!r}, Text={self.Text!r})"


class Conversations:
    """Represents the table Conversations in DB
    """
    _table_name = TABLE_NAME
    _db_table = None
    _engine = None

    def __init__(self, db_context: dict, engine=None, commit: bool = True):
        if engine is None:
            if self._engine is None:
                # db_context = DB_CONTEXT.get_context()
                self._engine = sqldb.create_engine(f'sqlite:///{db_context["db_file_path"]}')
            engine = self._engine
        connection = engine.connect()

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
        # Get max convo_id
        print('DB Update conversation')
        try:
            with Session(engine) as session:
                query = text(f'SELECT MAX(Id) from Conversations where InvocationId = {invocation_id}')
                result = session.execute(query)
                rows = result.fetchall()
                convo_id = rows[0][0]
                # get the id from above query
                # stmt = update(self._db_table).where([{
                #     'Id': convo_id, 'InvocationId': invocation_id}]).values([{
                #         'Text': text}])
                query = text(f'UPDATE Conversations SET Text = "{convo_text}" WHERE Id = {convo_id}')
                # stmt = update(self._db_table).where(
                #     Conversation.Id == convo_id
                # ).values(
                #     {"Text": convo_text}
                # )

            # stmt = insert(self._db_table).values([{
            #     'InvocationId': invocation_id,
            #     'SpokenTime': spoken_time,
            #     'Speaker': speaker_name,
            #     'Text': text}])

            # with Session(engine) as session:
                session.execute(query)
                session.commit()
                session.close()
        except Exception as ex:
            print(ex)

    @staticmethod
    def save_conversations(engine: Engine, data: list):
        # InvocationId is the current invocation
        # Data is a list of tuples.
        # Each tuple is of the format (InvocationId, time in utc, speaker, Text)

        # TODO: Will have to create engine here

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
