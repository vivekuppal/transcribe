# Experimental SenseVoiceSmall Backend

SenseVoiceSmall is available as an optional, Windows-only speech-to-text backend. It supports ordinary file transcription and Transcribe's existing chunk-based live transcription. This integration does not implement FunASR's streaming Paraformer protocol.

## Installation

SenseVoice support currently requires Python 3.11. Create the Transcribe virtual environment with Python 3.11 if needed:

```bat
py -3.11 -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r app\transcribe\requirements.txt
```

Then run the Windows setup script from the repository root:

```bat
app\transcribe\setup-sensevoice.bat
```

The script installs matching CPU builds of PyTorch 2.11 and TorchAudio 2.11, followed by the optional dependencies in `requirements-sensevoice.txt`. It stops with an error if the virtual environment is not using Python 3.11.

The model files are downloaded from Hugging Face on first use. SenseVoice model weights use the FunASR Model Open Source License Agreement rather than the Transcribe project license. Review the license before distributing the model files or a bundled application.

## Usage

Select the backend on the command line:

```bat
venv\Scripts\python.exe -m app.transcribe.main -stt sensevoice
```

Transcribe a file without starting the desktop interface:

```bat
venv\Scripts\python.exe -m app.transcribe.main -stt sensevoice -t C:\path\to\audio.wav
```

The default configuration is:

```yaml
SenseVoice:
  model: 'FunAudioLLM/SenseVoiceSmall'
  device: 'auto'
  use_itn: True
```

`device: auto` uses CUDA when PyTorch detects a compatible GPU and otherwise uses the CPU. SenseVoiceSmall directly supports Chinese, English, Cantonese, Japanese, and Korean. Other configured languages use automatic language detection.
