"""Unit tests for runtime state composition."""

import unittest

from app.transcribe.core.state import T_GLOBALS, TranscriptionGlobals, create_app_runtime


class TestRuntimeState(unittest.TestCase):
    def test_create_app_runtime_returns_distinct_instances(self):
        runtime_a = create_app_runtime()
        runtime_b = create_app_runtime()

        self.assertIsNot(runtime_a, runtime_b)
        self.assertIsNot(runtime_a.convo, runtime_b.convo)

    def test_transcription_globals_returns_compatibility_singleton(self):
        self.assertIs(TranscriptionGlobals(), T_GLOBALS)
        self.assertIs(TranscriptionGlobals(), TranscriptionGlobals())


if __name__ == "__main__":
    unittest.main()
