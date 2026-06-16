# Optional Speaker Diarization

Transcribe can optionally label speakers within Whisper and whisper.cpp transcripts using pyannote.audio.

This feature is disabled by default because it adds a larger PyTorch-based dependency stack and requires access to a Hugging Face diarization model.

## Install

Run the normal setup first, then install the optional diarization dependencies:

```powershell
app\transcribe\setup-diarization.bat
```

The diarization setup reinstalls CUDA-enabled PyTorch wheels after installing pyannote, because pyannote's dependency resolution can otherwise leave the environment with CPU-only Torch.

## Configure

Accept the model terms on Hugging Face for the configured pyannote model, create a Hugging Face access token, and set it as an environment variable:

```powershell
$env:HUGGINGFACE_TOKEN = "your-token"
```

Then enable diarization in `app\transcribe\override.yaml`:

```yaml
Diarization:
  enabled: True
```

The default model is `pyannote/speaker-diarization-community-1`.

## Behavior

When enabled, Whisper and whisper.cpp transcript segments are aligned with pyannote speaker turns. Transcribe displays source-specific speaker labels such as `Speaker 1`, `Speaker 2`, `You 1`, and `You 2`.

Speaker labels are assigned independently for microphone and speaker-output audio streams.
