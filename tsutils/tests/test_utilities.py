import unittest
from unittest.mock import patch, mock_open, call, MagicMock
import os
import subprocess
import time
import zipfile
import openai
from tsutils.utilities import (
    merge, delete_files, incrementing_filename, naturalsize,
    download_using_bits, zip_files_in_folder_with_params,
    zip_files_in_folder, get_available_models, is_api_key_valid,
    ensure_directory_exists, get_data_path, delete_old_files
)


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


if __name__ == '__main__':
    unittest.main()
