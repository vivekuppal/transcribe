from __future__ import annotations
import os
import copy
import subprocess
import zipfile
import openai
from appdirs import user_data_dir
import time

valid_api_key: bool = False


def merge(first: dict, second: dict, path=[]):
    """Recursively merge two dictionaries.
       For keys with different values, values in the second dictionary
       replace the values with current dictionary
    """
    if second is None:
        # No values to merge into first dict. Leave first dict unchanged.
        return first
    if first is None:
        # First dict does not exist as yet, but second does.
        # Make a deepcopy of second and append to first
        first = copy.deepcopy(second)
        return first

    for key in second:
        if key in first:
            if isinstance(first[key], dict) and isinstance(second[key], dict):
                merge(first[key], second[key], path + [str(key)])
            elif first[key] != second[key]:
                # print(f'Replacing the value of {key} from {first[key]} to {second[key]}')
                first[key] = second[key]
        else:
            first[key] = second[key]
    return first


def delete_files(file_list: list) -> bool:
    """Delete all files in the list
    """
    if not file_list:
        return True

    for file_name in file_list:
        if os.path.exists(file_name):
            os.remove(file_name)

    return True


def incrementing_filename(filename: str, extension: str):
    """Create a filename with incrementing number depending on the next available
    filename. Include dir path in filename if needed.
    Do not include . in the extension
    e.g. text-1.txt
    or text-2.txt if text-1.txt exists
    """
    i = 0
    while os.path.exists(f'{filename}-{i}.{extension}'):
        i += 1
    return f'{filename}-{i}.{extension}'

# The method naturalize is copied from
# https://github.com/python-humanize/humanize/blob/main/src/humanize/filesize.py
# Bits and bytes related humanization.


suffixes = {
    "decimal": (" kB", " MB", " GB", " TB", " PB", " EB", " ZB", " YB"),
    "binary": (" KiB", " MiB", " GiB", " TiB", " PiB", " EiB", " ZiB", " YiB"),
    "gnu": "KMGTPEZY",
}


def naturalsize(
    value: float | str,
    binary: bool = False,
    gnu: bool = False,
    str_format: str = "%.1f",
) -> str:
    """Format a number of bytes like a human readable filesize (e.g. 10 kB).

    By default, decimal suffixes (kB, MB) are used.

    Non-GNU modes are compatible with jinja2's `filesizeformat` filter.

    Examples:
        ```pycon
        >>> naturalsize(3000000)
        '3.0 MB'
        >>> naturalsize(300, False, True)
        '300B'
        >>> naturalsize(3000, False, True)
        '2.9K'
        >>> naturalsize(3000, False, True, "%.3f")
        '2.930K'
        >>> naturalsize(3000, True)
        '2.9 KiB'
        >>> naturalsize(10**28)
        '10000.0 YB'
        >>> naturalsize(-4096, True)
        '-4.0 KiB'

        ```

    Args:
        value (int, float, str): Integer to convert.
        binary (bool): If `True`, uses binary suffixes (KiB, MiB) with base
            2<sup>10</sup> instead of 10<sup>3</sup>.
        gnu (bool): If `True`, the binary argument is ignored and GNU-style
            (`ls -sh` style) prefixes are used (K, M) with the 2**10 definition.
        format (str): Custom formatter.

    Returns:
        str: Human readable representation of a filesize.
    """
    if gnu:
        suffix = suffixes["gnu"]
    elif binary:
        suffix = suffixes["binary"]
    else:
        suffix = suffixes["decimal"]

    base = 1024 if (gnu or binary) else 1000
    bytes_ = float(value)
    abs_bytes = abs(bytes_)

    if abs_bytes == 1 and not gnu:
        return f"{bytes_} Byte"

    if abs_bytes < base and not gnu:
        return f"{bytes_} Bytes"

    if abs_bytes < base and gnu:
        return f"{bytes_}B"

    for i, s in enumerate(suffix):
        unit = base ** (i + 2)

        if abs_bytes < unit:
            break

    ret: str = str_format % (base * bytes_ / unit) + s
    return ret


def download_using_bits(file_url: str, file_path: str):
    """Download a file using the BITS Service on windows
    """
    try:
        print(f'Downloading file: {file_url}')
        subprocess.check_output(['powershell',
                                 '-NoProfile',
                                 '-ExecutionPolicy',
                                 'Bypass',
                                 '-Command',
                                 'Start-BitsTransfer',
                                 '-Source',
                                 file_url,
                                 '-Destination',
                                 file_path]).strip()
    except subprocess.CalledProcessError:
        print(f'Failed to download the file: {file_url}')
    except FileNotFoundError:
        print('Please install Powershell or ensure it is in path.')
        print('Powershell is required to download models and install ffmpeg')


def zip_files_in_folder_with_params(**params):
    """Zip all files in the specified folder.
    This method is similar to zip_files_in_folder, can be called in 
    thread invocations
    """
    try:
        folder_path = params['folder_path']
        zip_file_name = params['zip_file_name']
        skip_zip_files = bool(params['skip_zip_files'])
    except KeyError as ke:
        print(f'Caught exception in method: {zip_files_in_folder_with_params}')
        print(f'Required argument {ke} not set.')

    zip_files_in_folder(folder_path=folder_path,
                        zip_file_name=zip_file_name,
                        skip_zip_files=skip_zip_files)


def zip_files_in_folder(folder_path: str, zip_file_name: str,
                        skip_zip_files: bool = True):
    """Zip all files in this folder
    """
    with zipfile.ZipFile(f'{zip_file_name}', 'w') as my_zip:
        for file in os.listdir(folder_path):
            if skip_zip_files and file.endswith(".zip"):
                continue
            my_zip.write(f'{folder_path}/{file}')


def get_available_models(client: openai.OpenAI) -> list:
    """Get the list of available models from the provider.
    """
    try:
        models = client.models.list()
        return_val = []
        for model in models.data:
            return_val.append(model.id)
    except openai.AuthenticationError as e:
        print(e)
        return None

    return sorted(return_val)


def is_api_key_valid(api_key: str, base_url: str, model: str) -> bool:
    """Check if it is valid openai compatible openai key for the provider
    """

    global valid_api_key  # pylint: disable=W0603

    if valid_api_key:
        return True

    if api_key == 'API_KEY':  # This is the default value
        return False

    openai.api_key = api_key
    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    try:
        # Ideally models list is the best way to determine if api key is valid
        # Some of the OpenAI compatible vendors do not support all the methods though
        # client.models.list()
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    'role': 'system',
                    'content': 'You are an AI assistant',
                },
                {
                    'role': 'user',
                    'content': 'Are you online',
                }
            ],
            model=model,
            # Openai model 03-mini does not support max_tokens parameter.
            # We do not support this model out of the box.
            # Comment this line to use 03-mini model
            max_tokens=1024
            # max_completion_tokens=1024
            )
        assert len(chat_completion.choices[0].message.content) > 0
        client.close()
    except openai.AuthenticationError as e:
        print(e)
        return False

    valid_api_key = True
    return True


def ensure_directory_exists(directory_path: str):
    """
    Ensure that a directory exists. If it does not exist, create it.

    Args:
        directory_path (str): The path to the directory to check or create.

    Returns:
        None
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    #    print(f"Directory '{directory_path}' created.")
    # else:
    #     print(f"Directory '{directory_path}' already exists.")


def get_data_path(app_name, filename=''):
    """
    Get the full path to the data file in the user data directory.
    These files are created inside the Roaming profile.

    Args:
        app_name (str): Specific folder inside the data dir like Log, Db, Cache
        filename (str): The name of the file.

    Returns:
        str: The full path to the data file.
    """
    data_dir = user_data_dir(app_name, appauthor='viveku', roaming=True)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return os.path.join(data_dir, filename)


def delete_old_files(folder_path: str, days: int):
    """
    Delete all files older than a specified number of months inside a folder.

    Args:
        folder_path (str): The path to the folder.
        months (int): The number of months. Files older than this will be deleted.

    Returns:
        None
    """
    current_time = time.time()
    cutoff_time = current_time - (days * 24 * 60 * 60)  # Days in seconds

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        # Check if it's a file (not a directory)
        if os.path.isfile(file_path):
            file_mod_time = os.path.getmtime(file_path)

            # Delete the file if it's older than the cutoff time
            if file_mod_time < cutoff_time:
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
