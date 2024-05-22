import unittest
from sqlalchemy.sql import text
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from llm_responses import LLMResponses  # Replace 'your_module' with the actual module name


class TestLLMResponses(unittest.TestCase):
    """Unit tests for the LLMResponses class.
    """

    @classmethod
    def setUpClass(cls):
        """Set up an in-memory SQLite database for testing.
        """
        cls.engine = create_engine('sqlite:///:memory:', echo=False)
        cls.Session = sessionmaker(bind=cls.engine)
        cls.llm_responses = LLMResponses(cls.engine)
        # cls.llm_responses.create_table()

    def setUp(self):
        """Ensure the table is created before each test.
        """
        metadata = self.llm_responses._metadata
        metadata.create_all(self.engine)

    def test_table_creation(self):
        """Test if the LLMResponses table is created successfully.
        """
        inspector = inspect(self.engine)
        self.assertIn(LLMResponses._table_name, inspector.get_table_names())

    def test_insert_response(self):
        """Test inserting a response into the LLMResponses table.
        """
        invocation_id = 1
        conversation_id = 2
        insert_text = "Test response"

        response_id = self.llm_responses.insert_response(
            invocation_id=invocation_id,
            conversation_id=conversation_id,
            text=insert_text,
            engine=self.engine
        )

        # Verify insertion
        session = self.Session()
        stmt = text(f'SELECT * FROM {LLMResponses._table_name} WHERE Id = :id')
        result = session.execute(stmt, [{'id': response_id}]).fetchone()
        session.close()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], invocation_id, 'invocation id do not match')
        self.assertEqual(result[3], conversation_id, 'conversation id do not match')
        self.assertEqual(result[4], insert_text, 'text do not match')

    def test_insert_response_auto_increment(self):
        """Test if the Id column auto-increments correctly."""
        invocation_id = 1
        conversation_id = 2
        insert_text = "First response"

        first_response_id = self.llm_responses.insert_response(
            invocation_id=invocation_id,
            conversation_id=conversation_id,
            text=insert_text,
            engine=self.engine
        )

        invocation_id = 3
        conversation_id = 4
        insert_text = "Second response"

        second_response_id = self.llm_responses.insert_response(
            invocation_id=invocation_id,
            conversation_id=conversation_id,
            text=insert_text,
            engine=self.engine
        )

        self.assertEqual(second_response_id, first_response_id + 1)

    def tearDown(self):
        """Drop the table after each test to ensure a clean state."""
        self.llm_responses._metadata.drop_all(self.engine)


if __name__ == '__main__':
    unittest.main()
