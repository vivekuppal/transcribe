import unittest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from summaries import Summary, Summaries  # Replace 'your_module' with the actual module name


class TestSummaries(unittest.TestCase):
    """Unit tests for the Summaries class."""

    @classmethod
    def setUpClass(cls):
        """Set up an in-memory SQLite database for testing."""
        cls.engine = create_engine('sqlite:///:memory:', echo=False)
        cls.Session = sessionmaker(bind=cls.engine)
        cls.summaries = Summaries(cls.engine)

    def setUp(self):
        """Ensure the table is created before each test."""
        metadata = self.summaries._db_table.metadata
        metadata.create_all(self.engine)

    def tearDown(self):
        """Drop the table after each test to ensure a clean state."""
        metadata = self.summaries._db_table.metadata
        metadata.drop_all(self.engine)

    def test_table_creation(self):
        """Test if the Summaries table is created successfully."""
        inspector = inspect(self.engine)
        self.assertIn(Summaries._table_name, inspector.get_table_names())

    def test_insert_summary(self):
        """Test inserting a summary into the Summaries table."""
        invocation_id = 1
        conversation_id = 1
        text = "This is a summary."

        summary_id = self.summaries.insert_summary(
            invocation_id=invocation_id,
            conversation_id=conversation_id,
            text=text
        )

        # Verify insertion
        session = self.Session()
        result = session.get(Summary, summary_id)
        session.close()

        self.assertIsNotNone(result)
        self.assertEqual(result.Id, summary_id)
        self.assertEqual(result.InvocationId, invocation_id)
        self.assertEqual(result.ConversationId, conversation_id)
        self.assertEqual(result.Text, text)


if __name__ == '__main__':
    unittest.main()
