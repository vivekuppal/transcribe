import unittest
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from db.conversation import Conversation, Conversations


class TestConversations(unittest.TestCase):
    """Unit tests for the Conversations class."""

    @classmethod
    def setUpClass(cls):
        """Set up an in-memory SQLite database for testing."""
        cls.engine = create_engine('sqlite:///:memory:', echo=False)
        cls.Session = sessionmaker(bind=cls.engine)
        cls.conversations = Conversations(cls.engine)

    def setUp(self):
        """Ensure the table is created before each test."""
        metadata = self.conversations._db_table.metadata
        metadata.create_all(self.engine)

    def tearDown(self):
        """Drop the table after each test to ensure a clean state."""
        metadata = self.conversations._db_table.metadata
        metadata.drop_all(self.engine)

    def test_table_creation(self):
        """Test if the Conversations table is created successfully."""
        inspector = inspect(self.engine)
        self.assertIn(Conversations._table_name, inspector.get_table_names())

    def test_insert_conversation(self):
        """Test inserting a conversation into the Conversations table."""
        invocation_id = 1
        spoken_time = datetime.utcnow()
        speaker_name = "John Doe"
        convo_text = "Hello, this is a test conversation."

        convo_id = self.conversations.insert_conversation(
            invocation_id=invocation_id,
            spoken_time=spoken_time,
            speaker_name=speaker_name,
            convo_text=convo_text
        )

        # Verify insertion
        session = self.Session()
        result = session.get(Conversation, convo_id)
        session.close()

        self.assertIsNotNone(result)
        self.assertEqual(result.Id, convo_id)
        self.assertEqual(result.InvocationId, invocation_id)
        self.assertEqual(result.SpokenTime, spoken_time)
        self.assertEqual(result.Speaker, speaker_name)
        self.assertEqual(result.Text, convo_text)

    def test_get_max_convo_id(self):
        """Test retrieving the ID of the last conversation entry for a given speaker."""
        invocation_id = 1
        spoken_time = datetime.utcnow()
        speaker_name = "John Doe"
        convo_text = "This is the latest conversation."

        self.conversations.insert_conversation(
            invocation_id=invocation_id,
            spoken_time=spoken_time,
            speaker_name=speaker_name,
            convo_text=convo_text
        )

        max_convo_id = self.conversations.get_max_convo_id(speaker_name, inv_id=invocation_id)

        # Verify retrieval
        session = self.Session()
        result = session.get(Conversation, max_convo_id)
        session.close()

        self.assertIsNotNone(result)
        self.assertEqual(result.Speaker, speaker_name)
        self.assertEqual(result.Text, convo_text)

    def test_update_conversation(self):
        """Test updating a conversation entry in the Conversations table."""
        invocation_id = 1
        spoken_time = datetime.utcnow()
        speaker_name = "John Doe"
        convo_text = "Initial conversation text."

        convo_id = self.conversations.insert_conversation(
            invocation_id=invocation_id,
            spoken_time=spoken_time,
            speaker_name=speaker_name,
            convo_text=convo_text
        )

        new_convo_text = "Updated conversation text."
        self.conversations.update_conversation(convo_id, new_convo_text)

        # Verify update
        session = self.Session()
        result = session.get(Conversation, convo_id)
        session.close()

        self.assertIsNotNone(result)
        self.assertEqual(result.Text, new_convo_text)


if __name__ == '__main__':
    unittest.main()
