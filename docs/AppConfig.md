# Application Configuration


Note: Any changes to default configuration should be done with appropriate care and pay attention to the instructions for those configurations.

Transcribe is customizable in many different ways. A number of configuration options are specified in `parameters.yaml` file.

We wish that it is very easy to
- Override default configuration
- Return to default settings


## Override Default Config
To alter any default configuration specified in `parameters.yaml` file make the same section, element in `override.yaml`.

E.g.

Default Log file name is `Transcribe.log`. This is specified in `parameters.yaml` as 

```yaml
General:
  log_file: 'Transcribe.log'
```

To change it to a different filename create a similar section in override.yaml file

```yaml
General:
  log_file: 'CustomLogFileName.log'
```

Details of specific elements are available in `parameters.yaml` file itself.

## Revert to Default Config
Remove all contents of `override.yaml` file to rever the applicationn to Default config.
