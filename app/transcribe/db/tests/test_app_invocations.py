import unittest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app_invocations import Invocation, ApplicationInvocations


class TestApplicationInvocations(unittest.TestCase):
    """Unit tests for the ApplicationInvocations class."""

    @classmethod
    def setUpClass(cls):
        """Set up an in-memory SQLite database for testing."""
        cls.engine = create_engine('sqlite:///:memory:', echo=False)
        cls.Session = sessionmaker(bind=cls.engine)
        cls.app_invocations = ApplicationInvocations(cls.engine)

    def setUp(self):
        """Ensure the table is created before each test."""
        metadata = self.app_invocations._db_table.metadata
        metadata.create_all(self.engine)

    def tearDown(self):
        """Drop the table after each test to ensure a clean state."""
        metadata = self.app_invocations._db_table.metadata
        metadata.drop_all(self.engine)

    def test_table_creation(self):
        """Test if the ApplicationInvocations table is created successfully."""
        inspector = inspect(self.engine)
        self.assertIn(ApplicationInvocations._table_name, inspector.get_table_names())

    def test_insert_start_time(self):
        """Test inserting a start time into the ApplicationInvocations table."""
        self.app_invocations.insert_start_time(self.engine)
        invocation_id = self.app_invocations.get_invocation_id()

        # Verify insertion
        session = self.Session()
        result = session.get(Invocation, invocation_id)
        session.close()

        self.assertIsNotNone(result)
        self.assertEqual(result.Id, invocation_id)
        self.assertIsNotNone(result.StartTime)
        self.assertIsNone(result.EndTime)

    def test_populate_end_time(self):
        """Test updating the end time of the current invocation."""
        self.app_invocations.insert_start_time(self.engine)
        self.app_invocations.populate_end_time(self.engine)

        invocation_id = self.app_invocations.get_invocation_id()

        # Verify update
        session = self.Session()
        result = session.get(Invocation, invocation_id)
        session.close()

        self.assertIsNotNone(result)
        self.assertEqual(result.Id, invocation_id)
        self.assertIsNotNone(result.EndTime)

    def test_get_invocation_id(self):
        """Test retrieving the invocation ID of the current application instance."""
        self.app_invocations.insert_start_time(self.engine)
        invocation_id = self.app_invocations.get_invocation_id()

        # Verify invocation ID
        self.assertIsNotNone(invocation_id)
        self.assertIsInstance(invocation_id, int)


if __name__ == '__main__':
    unittest.main()
