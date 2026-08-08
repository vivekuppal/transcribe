# Application Configuration


Note: Any changes to default configuration should be done with appropriate care and pay attention to the instructions for those configurations.

Transcribe is customizable in many different ways. A number of configuration options are specified in `parameters.yaml` file.

We wish that it is very easy to
- Override default configuration
- Return to default settings


## Override Default Config
To alter any default configuration specified in `parameters.yaml` file make the same section, element in `override.yaml`.

E.g.

Default Log file name is `logs/Transcribe.log`. This is specified in `parameters.yaml` as 

```yaml
General:
  log_file: 'logs/Transcribe.log'
```

To change it to a different filename create a similar section in override.yaml file

```yaml
General:
  log_file: 'CustomLogFileName.log'
```

Details of specific elements are available in `parameters.yaml` file itself.

Realtime transcription has its own `OpenAIRealtime` section so response-LLM settings and streaming STT settings remain independent. It reuses only `OpenAI.api_key`:

```yaml
OpenAIRealtime:
  model: 'gpt-live-transcribe'
  delay: 'low'
  reconnect_attempts: 3
```

See [OpenAI Realtime transcription](./OpenAIRealtime.md) for all supported values and operational behavior.

## Revert to Default Config
Remove all contents of `override.yaml` file to rever the applicationn to Default config.
