# OpenAI API Compatible Provider Support #

Transcribe supports all Providers who are API compatible with OpenAI API specification.
- Azure
- Perplexity
- Together

To choose a specific provider add the following section to `override.yaml` file

```
OpenAI:
  api_key: 'PROVIDER_SPECIFIC_API_KEY'
  base_url: 'BASE_URL_FOR_PROVIDER'
  ai_model: 'MODEL_OF_CHOICE'
```

Default `base_url` for OpenAI is `https://api.openai.com/v1`
Default `ai_model` for OpenAI is `gpt-5.6-luna`. Model IDs are passed through
unchanged, so another OpenAI model or a model exposed by a compatible provider
can be selected without a code change.

Optional request parameters can be configured independently. Leave either value
as `null` when the selected model does not support it:

```yaml
OpenAI:
  temperature: null
  reasoning_effort: low
```

This compatibility configuration applies to response generation. The optional `openai-realtime` STT backend connects specifically to OpenAI's Realtime WebSocket API and is configured separately under `OpenAIRealtime`; it should not be confused with the Whisper API selected by `-stt whisper --api`.

Our users have found this to be very useful in countries like Australia and China, where they cannot access the default providers directly or it is cost prohibitive to access these providers.

## Deepgram Speech To Text

The default Deepgram STT model is `nova-3`, configured in `parameters.yaml`:

```yaml
Deepgram:
  model: 'nova-3'
```

Deepgram describes Nova-3 as its current high-accuracy general transcription model. For Transcribe's chunked live transcription path, this uses Deepgram's pre-recorded transcription endpoint rather than a native streaming protocol.
