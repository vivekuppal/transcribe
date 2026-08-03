# OpenAI Realtime Transcription

Transcribe can use OpenAI's `gpt-live-transcribe` model as an optional native streaming speech-to-text backend. This is different from the existing Whisper API mode: Whisper API repeatedly uploads recorded WAV windows, while OpenAI Realtime keeps a WebSocket session open and returns transcript deltas as audio arrives.

## Setup

Install the normal source dependencies with `setup.bat`, then place an OpenAI API key in `app/transcribe/override.yaml`:

```yaml
OpenAI:
  api_key: 'YOUR_OPENAI_API_KEY'
```

Do not commit `override.yaml`. API billing is separate from a ChatGPT subscription, and the account must have API billing enabled. OpenAI currently lists `gpt-live-transcribe` at **$0.017 per realtime audio minute**; verify the current rate on the [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-live-transcribe) before deployment.

Run from `app/transcribe`:

```powershell
python main.py -stt openai-realtime
```

The `-a`/`--api` switch is not required. That switch continues to mean the existing Whisper file API when `-stt whisper` is selected.

## Audio and source separation

The backend creates one independent WebSocket session per enabled source:

```text
Microphone -> OpenAI Realtime session -> You
Windows WASAPI loopback -> OpenAI Realtime session -> Speaker
```

Each stream is converted independently from its actual device format to mono, signed PCM16 at 24 kHz. Resampling state and incomplete PCM frames are retained across capture-block boundaries to avoid gaps and duplicates. Disabling the microphone or speaker closes only that source's session; pausing transcription closes both sessions.

`Speaker` contains everything played through the selected Windows loopback device. Discord normally mixes all remote participants into that output. Transcribe therefore distinguishes `You` from `Speaker`, but `gpt-live-transcribe` does not identify individual remote participants.

## Partial and final text

OpenAI Realtime emits replaceable transcript deltas and a confirmed `completed` event for each item. Transcribe displays the current partial text through its main-thread UI queue, but only the confirmed transcript is inserted into `Conversation`, the database, LLM context, and **Save Transcript to File** output. Events are reconciled by OpenAI `item_id`, so repeated completion events do not duplicate transcript rows.

## Turn detection

The default uses OpenAI server VAD. It sends audio continuously while OpenAI detects silence and commits each turn:

```yaml
OpenAIRealtime:
  turn_detection: 'server_vad'
  vad_threshold: 0.5
  vad_prefix_padding_ms: 300
  vad_silence_duration_ms: 500
```

Set `turn_detection: null` only for development with an integration that calls the streaming client's manual `commit()` method. The desktop adapter currently uses server VAD.

## Configuration

All Realtime-specific values are separate from LLM response configuration and may be overridden in `override.yaml`:

```yaml
OpenAIRealtime:
  model: 'gpt-live-transcribe'
  input_sample_rate: 24000
  turn_detection: 'server_vad'
  delay: 'low'
  capture_chunk_duration_ms: 100
  reconnect_attempts: 3
  reconnect_backoff_seconds: 2
  max_buffered_chunks: 120
  max_raw_audio_chunks: 240
  event_queue_size: 500
  deduplication_cache_size: 2048
```

Supported delay presets are `minimal`, `low`, `medium`, `high`, and `xhigh`. Lower delay produces earlier partials; higher delay gives the model more context. The OpenAI API may reject unsupported language codes or invalid keyword hints.

## Reliability, cost, and privacy

- Microphone and speaker sessions reconnect independently with a bounded backoff.
- Audio waiting for a temporarily disconnected socket is bounded. Per-session overflow is reported as an error.
- The shared capture ingress is also bounded; if it fills, the oldest block is replaced so latency and memory remain bounded.
- Provider item IDs are retained in a bounded cache to suppress duplicate completions without growing for the application lifetime.
- Two enabled sources mean two independently processed live streams and corresponding API usage.
- Audio is sent to OpenAI for transcription. Review OpenAI's current data controls and your organization's privacy requirements.
- The application's existing shutdown flow may also save microphone and speaker WAV recordings in its local application-data directory; Realtime mode does not add audio to logs.
- Inform and obtain any required consent from participants before recording or transcribing them. Laws and workplace policies vary by location.
- API keys, authorization headers, and raw audio are not written to application logs.

The model does not provide word-level timestamps, confidence scores, or speaker labels. Use one of the existing file/window backends if those features are required.

## Optional live smoke test

Normal tests use simulated WebSockets and require no device, network, key, or paid account. To verify only that a real session can connect and close:

```powershell
$env:TRANSCRIBE_OPENAI_REALTIME_SMOKE = '1'
$env:OPENAI_API_KEY = 'YOUR_OPENAI_API_KEY'
python -m unittest -v app.transcribe.tests.test_openai_realtime_model.TestOpenAIRealtimeSmoke
```
