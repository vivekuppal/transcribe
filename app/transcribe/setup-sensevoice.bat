@echo off
setlocal enabledelayedexpansion

set "PYTHON=%~dp0..\..\venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Transcribe virtual environment not found. Run setup.bat first.
    exit /b 1
)

echo Checking Python version...
"%PYTHON%" -c "import sys; exit(0 if sys.version_info[:2] == (3,11) else 1)"

if errorlevel 1 (
    echo SenseVoice currently requires Python 3.11 for Transcribe.
    echo Recreate the venv with: py -3.11 -m venv venv
    exit /b 1
)

echo Upgrading pip...
"%PYTHON%" -m pip install --upgrade pip

if errorlevel 1 (
    echo Could not upgrade pip.
    exit /b 1
)

echo Installing PyTorch and TorchAudio CPU builds...
"%PYTHON%" -m pip install torch==2.11.0 torchaudio==2.11.0 --index-url "https://download.pytorch.org/whl/cpu"

if errorlevel 1 (
    echo Could not install PyTorch and TorchAudio CPU builds.
    exit /b 1
)

echo Installing optional SenseVoice dependencies...
"%PYTHON%" -m pip install -r "%~dp0requirements-sensevoice.txt"

if errorlevel 1 (
    echo Could not install the optional SenseVoice dependencies.
    exit /b 1
)

echo Verifying installation...
"%PYTHON%" -c "import torch, torchaudio, funasr, modelscope; from funasr import AutoModel; print('torch=' + torch.__version__); print('torchaudio=' + torchaudio.__version__); print('funasr=' + funasr.__version__); print('modelscope=' + modelscope.__version__)"

if errorlevel 1 (
    echo SenseVoice dependency verification failed.
    exit /b 1
)

echo SenseVoice dependencies installed successfully.
exit /b 0
