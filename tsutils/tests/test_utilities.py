import unittest
from unittest.mock import patch
import openai
from tsutils.utilities import (
    merge, incrementing_filename, naturalsize,
    download_using_bits, ensure_directory_exists, is_api_key_valid
)
import tsutils.utilities as utilities


class TestFunctions(unittest.TestCase):

    def test_merge(self):
        first = {'a': 1, 'b': {'c': 3}}
        second = {'b': {'d': 4}, 'e': 5}
        result = merge(first, second)
        self.assertEqual(result, {'a': 1, 'b': {'c': 3, 'd': 4}, 'e': 5})

    @patch('os.path.exists', side_effect=[True, True, False])
    def test_incrementing_filename(self, mock_exists):
        result = incrementing_filename('file', 'txt')
        self.assertEqual(result, 'file-2.txt')

    def test_naturalsize(self):
        result = naturalsize(3000000)
        self.assertEqual(result, '3.0 MB')
        result = naturalsize(300, False, True)
        self.assertEqual(result, '300.0B', f'Expected 300.0B got {result}')

    @patch('subprocess.check_output')
    def test_download_using_bits(self, mock_subproc):
        download_using_bits('https://github.com/vivekuppal/transcribe/archive/refs/heads/main.zip', 'transcribe.zip')
        mock_subproc.assert_called_once_with(['powershell',
                                              '-NoProfile',
                                              '-ExecutionPolicy',
                                              'Bypass',
                                              '-Command',
                                              'Start-BitsTransfer',
                                              '-Source',
                                              'https://github.com/vivekuppal/transcribe/archive/refs/heads/main.zip',
                                              '-Destination',
                                              'transcribe.zip'])

    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    def test_ensure_directory_exists(self, mock_exists, mock_makedirs):
        ensure_directory_exists('.')
        mock_makedirs.assert_called_once_with('.')

    @patch('tsutils.utilities.openai.OpenAI')
    def test_is_api_key_valid_returns_false_for_openai_provider_errors(self, mock_openai):
        utilities.valid_api_key = False
        client = mock_openai.return_value
        client.chat.completions.create.side_effect = openai.OpenAIError('model not available')

        self.assertFalse(is_api_key_valid(
            api_key='key',
            base_url='https://api.example.com',
            model='unavailable-model',
        ))


if __name__ == '__main__':
    unittest.main()
