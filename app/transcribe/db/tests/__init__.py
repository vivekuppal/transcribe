from sqlalchemy.orm import DeclarativeBase
from db.app_db import AppDB


class AppDBBase(DeclarativeBase):
    pass


DB_CONTEXT = AppDB()
