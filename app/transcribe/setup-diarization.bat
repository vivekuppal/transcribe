@echo off
REM Optional speaker diarization dependencies.
REM Run from the repository root after setup.bat:
REM   app\transcribe\setup-diarization.bat

call venv\scripts\activate.bat
python -m pip install -r app\transcribe\requirements-diarization.txt
REM pyannote.audio depends on torch and may resolve CPU wheels from PyPI.
REM Reinstall the CUDA-enabled PyTorch stack after pyannote so Whisper and diarization can use GPU.
python -m pip install --force-reinstall torch==2.11.0+cu126 torchaudio==2.11.0+cu126 torchcodec==0.14.0+cu126 --index-url https://download.pytorch.org/whl/cu126

echo Diarization dependencies installed.
echo Set HUGGINGFACE_TOKEN or Diarization.huggingface_token before enabling diarization.
