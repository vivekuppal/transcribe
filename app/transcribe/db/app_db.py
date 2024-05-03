# import os
import db.app_invocations as appi
import sqlalchemy as db
from sqlalchemy import Engine, Connection


class AppDB:
    _tables = [
        'ApplicationInvocations'
    ]
    _db_file_path = '../logs/app.db'

    def __init__(self):
        # Create DB file if it does not exist
        engine = db.create_engine('sqlite:///app.db', echo=True)
        connection = engine.connect()

        # Initialize all the tables
        appi.ApplicationInvocations(engine=engine, connection=connection, commit=False)
        connection.commit()
        connection.close()

    def initialize_app(self):
        engine: Engine = db.create_engine('sqlite:///app.db', echo=True)
        connection: Connection = engine.connect()
        appi.ApplicationInvocations(engine, connection).insert_start_time(engine=engine)

    def shutdown(self):
        engine = db.create_engine('sqlite:///app.db', echo=True)
        connection = engine.connect()
        appi.ApplicationInvocations(engine=engine, connection=connection, commit=False).populate_end_time(engine)
