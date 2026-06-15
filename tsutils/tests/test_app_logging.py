"""Tests for application logging configuration."""

import logging
import tempfile
import unittest
from unittest.mock import patch

from tsutils import app_logging


class TestAppLogging(unittest.TestCase):
    @patch("tsutils.app_logging.setup_logging")
    @patch("tsutils.app_logging.utilities.get_data_path")
    def test_application_logger_does_not_propagate_to_console(self, mock_data_path, _mock_setup):
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_data_path.return_value = temp_dir
            listener = app_logging.initiate_log(
                {"General": {"log_file": "transcribe.log"}}
            )

            try:
                self.assertFalse(app_logging.root_logger.propagate)
            finally:
                listener.stop()
                for handler in listener.handlers:
                    handler.close()
                for handler in list(app_logging.root_logger.handlers):
                    app_logging.root_logger.removeHandler(handler)
                    handler.close()
                app_logging.root_logger.propagate = True
                app_logging.root_logger.setLevel(logging.NOTSET)


if __name__ == "__main__":
    unittest.main()
