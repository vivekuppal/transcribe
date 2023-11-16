import sys
import copy
import yaml
import Singleton
import utilities


class Config(Singleton.Singleton):
    """A Singleton object with all configuration data
    """
    _default_config_filename:  str = None
    _override_config_filename: str = None
    _default_data: dict = None   # Data as read from parameters.yaml
    _override_data: dict = None  # Data as read from override.yaml
    _current_data: dict = None   # Merged data of parameters.yaml and override.yaml
    _initialized: bool = False

    def __init__(self, default_config_filename: str = 'parameters.yaml',
                 override_config_filename: str = 'override.yaml'):
        if self._initialized:
            return
        with open(default_config_filename, mode='r', encoding='utf-8') as default_config_file:
            try:
                if self._default_data is None:
                    self._default_data = yaml.load(stream=default_config_file, Loader=yaml.CLoader)
            except ImportError as err:
                print(f'Failed to load yaml file: {default_config_filename}.')
                print(f'Error: {err}')
                sys.exit(1)

        with open(override_config_filename, mode='r', encoding='utf-8') as override_config_file:
            try:
                if self._override_data is None:
                    self._override_data = yaml.load(stream=override_config_file,
                                                    Loader=yaml.CLoader)
            except ImportError as err:
                print(f'Failed to load yaml file: {override_config_filename}.')
                print(f'Error: {err}')
                sys.exit(1)

        self._default_config_filename = default_config_filename
        self._override_config_filename = override_config_filename

        # Merge default and override values
        self._current_data = copy.deepcopy(self._default_data)
        utilities.merge(self._current_data, self._override_data)
        self._initialized = True

    def add_override_value(self, input_dict: dict):
        """Override a default configuration parameter value
        """
        if not isinstance(input_dict, dict):
            print(f'Expected input value to be a dict. Instead received: {input_dict}')
        # Update the override values
        utilities.merge(self._override_data, input_dict)
        # update the current values
        utilities.merge(self._current_data, input_dict)
        # Write override values to file
        with open(file=self._override_config_filename, mode="w", encoding='utf-8') as override_file:
            yaml.dump(self._override_data, override_file, default_flow_style=False)

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
