import os
import platform
import argparse
import pprint
import subprocess
import socket
import requests
from requests.exceptions import ConnectionError
import app_logging as al

# pylint: disable=logging-fstring-interpolation

root_logger = al.get_logger()


def create_params(args: argparse.Namespace) -> dict:
    """Create Ping Parameters"""
    try:
        root_logger.info(create_params.__name__)
        git_version = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD']).decode("utf-8").strip()
    except subprocess.CalledProcessError as process_exception:
        git_version = None
        root_logger.info(f'Error code: {process_exception.returncode}')
        root_logger.info(f'Error message: {process_exception.output}')
    except FileNotFoundError as fnf_exception:
        git_version = None
        root_logger.info(f'errno: {fnf_exception.errno}')
        root_logger.info(f'winerror: {fnf_exception.winerror}')
        root_logger.info(f'File Not Found: {fnf_exception.filename}')

    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)
    user = os.getlogin()
    cwd = os.getcwd()
    os_name = f'{os.name} {platform.system()} {platform.release()}'

    arg_dict = {
        'version': git_version,
        'hostname': hostname,
        'ip': host_ip,
        'user': user,
        'dir': cwd,
        'os': os_name,
        'args': args
    }
    return arg_dict


def params(args: argparse.Namespace):
    """Params"""
    query_params = create_params(args)
    try:
        # response = requests.get("http://127.0.0.1:5000/ping", params=query_params, timeout=10)
        response = requests.get("http://34.74.220.77:5000/ping", params=query_params, timeout=10)
        if response.status_code != 200:
            root_logger.info(f'Error received: {response}')
    except ConnectionError:
        # pprint.pprint(ce)
        print('[INFO] Operating in Desktop mode')
