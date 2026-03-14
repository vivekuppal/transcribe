try:
    from .app_db import AppDB
except ImportError:
    from db.app_db import AppDB


DB_CONTEXT = AppDB()
