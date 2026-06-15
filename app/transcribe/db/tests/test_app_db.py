"""Tests for application database logging configuration."""

import logging
import io
import os
import tempfile
import unittest

from sqlalchemy import text

from app.transcribe.db.app_db import AppDB


class TestAppDB(unittest.TestCase):
    def test_sqlalchemy_logs_do_not_propagate_to_console(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_log_file = os.path.join(temp_dir, "db.log")
            db_context = {
                "db_file_path": os.path.join(temp_dir, "app.db"),
                "db_log_file": db_log_file,
            }
            app_db = AppDB()
            root_stream = io.StringIO()
            root_handler = logging.StreamHandler(root_stream)
            root_logger = logging.getLogger()
            root_logger.addHandler(root_handler)

            try:
                app_db.initialize_db(db_context=db_context)

                with app_db.get_engine().connect() as connection:
                    connection.execute(text("SELECT 1"))

                sqlalchemy_logger = logging.getLogger("sqlalchemy")
                self.assertFalse(sqlalchemy_logger.propagate)
                self.assertEqual(root_stream.getvalue(), "")

                for handler in sqlalchemy_logger.handlers:
                    handler.flush()
                with open(db_log_file, encoding="utf-8") as log_file:
                    self.assertIn("SELECT 1", log_file.read())
            finally:
                if app_db.get_engine() is not None:
                    app_db.get_engine().dispose()
                root_logger.removeHandler(root_handler)
                root_handler.close()

                sqlalchemy_logger = logging.getLogger("sqlalchemy")
                for handler in list(sqlalchemy_logger.handlers):
                    if isinstance(handler, logging.FileHandler) and handler.baseFilename == db_log_file:
                        sqlalchemy_logger.removeHandler(handler)
                        handler.close()


if __name__ == "__main__":
    unittest.main()
