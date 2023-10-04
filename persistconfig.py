"""Test file for checking persist functionality for configuration data
"""
import yaml
import configuration

YAML_FILE_NAME: str = './override.yaml'

if __name__ == "__main__":

    print('Executing persist yaml')
    y = configuration.Config()
    yaml_config: dict = y.data
    altered_config: dict = {'General': {'transcript_audio_duration_seconds': 20}}

    y.add_override_value(altered_config)

    with open(file=YAML_FILE_NAME, mode="w", encoding='utf-8') as f:
        yaml.dump(altered_config, f, default_flow_style=False)
