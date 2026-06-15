# Experimental SenseVoiceSmall Backend

SenseVoiceSmall is available as an optional, Windows-only speech-to-text backend. It supports ordinary file transcription and Transcribe's rolling-window live transcription. This integration does not implement FunASR's streaming Paraformer protocol.

## Installation

SenseVoice support currently requires Python 3.11 on Windows. Create the Transcribe virtual environment with Python 3.11 if needed:

```bat
py -3.11 -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r app\transcribe\requirements.txt
```

Verify that the virtual environment is using Python 3.11 before installing the optional SenseVoice packages:

```bat
venv\Scripts\python.exe --version
```

Then run the Windows setup script from the repository root:

```bat
app\transcribe\setup-sensevoice.bat
```

The script stops with an error if the virtual environment is not using Python 3.11. It preserves an existing CPU or CUDA PyTorch installation and installs the matching TorchAudio build. If PyTorch is not installed, it installs CPU builds of PyTorch 2.11 and TorchAudio 2.11. It then installs the optional dependencies in `requirements-sensevoice.txt`.

If the base environment already uses a CUDA-enabled PyTorch build, installing SenseVoice should not switch Whisper back to CPU. Verify the active build with:

```bat
venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## Model Download

The default model is `FunAudioLLM/SenseVoiceSmall`. Model files are downloaded from Hugging Face on first use, not during dependency installation. The first transcription can take longer while the model cache is populated.

The adapter explicitly uses the Hugging Face hub when loading the model. This avoids the slower international download path that can happen when the upstream default model source is used.

SenseVoice model weights use the FunASR Model Open Source License Agreement rather than the Transcribe project license. Review the model license before distributing the model files or a bundled application.

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

## Troubleshooting

If SenseVoice or Whisper is unexpectedly using CPU, check the PyTorch build inside the virtual environment:

```bat
venv\Scripts\python.exe -c "import torch; print('torch=' + torch.__version__); print('cuda_available=' + str(torch.cuda.is_available())); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

If `cuda_available=False`, the virtual environment has a CPU-only PyTorch build or the NVIDIA driver is not available to PyTorch. If `python app\transcribe\main.py` uses a different Python version, run the app with the virtual environment explicitly:

```bat
venv\Scripts\python.exe app\transcribe\main.py -stt sensevoice
```
