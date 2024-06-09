import unittest
from unittest.mock import patch
import datetime
from tsutils.duration import Duration


class TestDuration(unittest.TestCase):
    """Unit Tests for Duration class
    """

    @patch('datetime.datetime')
    def test_enter_method(self, mock_datetime):
        """Test that __enter__ method records the start time correctly."""
        mock_datetime.now.return_value = datetime.datetime(2023, 1, 1, 12, 0, 0)
        duration = Duration()
        with duration:
            self.assertEqual(duration.start, datetime.datetime(2023, 1, 1, 12, 0, 0))


if __name__ == '__main__':
    unittest.main()
