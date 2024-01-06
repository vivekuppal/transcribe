import sys
import time
import copy
import yaml
from tsutils import Singleton
from tsutils import utilities


CONFIG_REFRESH_INTERVAL_SECONDS = 10


class Config(Singleton.Singleton):
    """A Singleton object with all configuration data
    """
    _default_config_filename:  str = None
    _override_config_filename: str = None
    _default_data: dict = None   # Data as read from parameters.yaml
    _override_data: dict = None  # Data as read from override.yaml
    _current_data: dict = None   # Merged data of parameters.yaml and override.yaml
    _initialized: bool = False
    _refresh_period = CONFIG_REFRESH_INTERVAL_SECONDS
    _refresh_periodically = False

    def __init__(self, default_config_filename: str = 'parameters.yaml',
                 override_config_filename: str = 'override.yaml'):

        if self._initialized:
            return

        self._default_config_filename = default_config_filename
        self._override_config_filename = override_config_filename
        self.read_config_from_files()
        self._initialized = True

    def refresh(self):
        while True:
            time.sleep(CONFIG_REFRESH_INTERVAL_SECONDS)
            self.read_config_from_files()

    def read_config_from_files(self):
        """Read config data from yaml files
        """
        try:
            with open(self._default_config_filename, mode='r', encoding='utf-8') as default_config_file:
                self._default_data = yaml.load(stream=default_config_file, Loader=yaml.CLoader)

        except ImportError as err:
            print(f'Failed to load yaml file: {self._default_config_filename}.')
            print(f'Error: {err}')
            sys.exit(1)
        except FileNotFoundError as err:
            print(f'Failed to find yaml file: {self._default_config_filename}.')
            print(f'Error: {err}')
            sys.exit(1)

        try:
            with open(self._override_config_filename, mode='r', encoding='utf-8') as override_config_file:
                self._override_data = yaml.load(stream=override_config_file,
                                                Loader=yaml.CLoader)
        except ImportError as err:
            print(f'Failed to load yaml file: {self._override_config_filename}.')
            print(f'Error: {err}')
            sys.exit(1)
        except FileNotFoundError as err:
            print(f'Failed to find yaml file: {self._override_config_filename}.')
            print(f'Error: {err}')
            sys.exit(1)

        # Merge default and override values
        self._current_data = copy.deepcopy(self._default_data)
        self._current_data = utilities.merge(self._current_data, self._override_data)

    def add_override_value(self, input_dict: dict):
        """Override a default configuration parameter value
        """
        if not isinstance(input_dict, dict):
            print(f'Expected input value to be a dict. Instead received: {input_dict}')
        # Update the override values
        self._override_data = utilities.merge(self._override_data, input_dict)
        # update the current values
        self._current_data = utilities.merge(self._current_data, input_dict)
        # Write override values to file
        with open(file=self._override_config_filename, mode="w", encoding='utf-8') as override_file:
            yaml.dump(self._override_data, override_file, default_flow_style=False)

    @staticmethod
    def load_alter_save(section_name, property_name, value):
        """Load from config files, alter a value, save back to config files"""
        yml = Config()
        with open(yml.config_override_file, mode='r', encoding='utf-8') as file:
            try:
                altered_config = yaml.load(stream=file, Loader=yaml.CLoader)
                # Handle empty override file
                if altered_config is None:
                    altered_config = {}
            except ImportError as err:
                print(f'Failed to load yaml file: {yml.config_override_file}.')
                print(f'Error: {err}')
                sys.exit(1)

        if section_name not in altered_config:
            altered_config[section_name] = {}
        altered_config[section_name][property_name] = value
        yml.add_override_value(altered_config)

    @property
    def data(self) -> dict:
        """Get all configuration data read from yaml file"""
        return self._current_data

    @property
    def config_override_file(self) -> str:
        """Name of the yaml file used to override configuration"""
        return self._override_config_filename

    @property
    def config_file(self) -> str:
        """Name of the yaml file with default configuration"""
        return self._default_config_filename
