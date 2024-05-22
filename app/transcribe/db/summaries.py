import datetime
import sqlalchemy as sqldb
from sqlalchemy import Column, Integer, String, MetaData, DateTime
from sqlalchemy.orm import Session, mapped_column
from sqlalchemy import Engine, insert

TABLE_NAME = 'Summaries'


class Summary():
    """One row in the Summaries Table
    """
    __tablename__ = TABLE_NAME

    Id = mapped_column(Integer, primary_key=True, autoincrement=True)
    CreatedTime = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    InvocationId = mapped_column(Integer, nullable=False)
    ConversationId = mapped_column(Integer, nullable=False)
    Text = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"CreatedTime={self.CreatedTime!r}" \
               f"Invocation(id={self.Id!r}, " \
               f"ConversationId={self.ConversationId!r}," \
               f"Text={self.Text!r})"


class Summaries:
    """Represents the table Summaries in DB
    """
    _table_name = TABLE_NAME
    _db_table = None
    _metadata: MetaData = None

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

    def create_table(self, engine: Engine, metadata: MetaData):
        """Create summaries table in DB.
        """
        self._db_table = sqldb.Table(self._table_name, metadata,
                                     Column('Id', Integer(), sqldb.Identity(start=1),
                                            primary_key=True),
                                     Column('CreatedTime', DateTime, nullable=False,
                                            default=datetime.datetime.utcnow),
                                     Column("InvocationId", Integer, nullable=False),
                                     Column("ConversationId", Integer, nullable=False),
                                     Column('Text', String, nullable=False),
                                     )

        metadata.create_all(engine)

    def insert_summary(self, invocation_id: int,
                       conversation_id: int,
                       text: str,
                       engine: Engine) -> int:
        """Insert a summary entry
        """
        stmt = insert(self._db_table).values([{
            'InvocationId': invocation_id,
            'ConversationId': conversation_id,
            'Text': text,
            'CreatedTime': datetime.datetime.utcnow()}])

        with Session(engine) as session:
            result = session.execute(stmt)
            session.commit()
            session.close()

        return result.lastrowid

    def populate_data(self):
        """Not Implemented
        """
        pass   # pylint: disable=W0107
