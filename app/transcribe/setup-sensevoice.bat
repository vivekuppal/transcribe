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

echo Checking the installed PyTorch build...
"%PYTHON%" -c "import torch" >nul 2>&1

if errorlevel 1 (
    echo PyTorch is not installed. Installing CPU builds of PyTorch and TorchAudio...
    "%PYTHON%" -m pip install torch==2.11.0 torchaudio==2.11.0 --index-url "https://download.pytorch.org/whl/cpu"
) else (
    set "TORCH_INFO_FILE=%TEMP%\transcribe-torch-info-!RANDOM!.txt"
    "%PYTHON%" -c "import torch; print(torch.__version__.split('+')[0], 'cu' + torch.version.cuda.replace('.', '') if torch.version.cuda else 'cpu')" > "!TORCH_INFO_FILE!"
    for /f "usebackq tokens=1,2" %%A in ("!TORCH_INFO_FILE!") do (
        set "TORCH_VERSION=%%A"
        set "TORCH_FLAVOR=%%B"
    )
    del "!TORCH_INFO_FILE!"
    echo Preserving PyTorch !TORCH_VERSION! !TORCH_FLAVOR! and installing matching TorchAudio...
    "%PYTHON%" -m pip install torchaudio==!TORCH_VERSION! --index-url "https://download.pytorch.org/whl/!TORCH_FLAVOR!"
)

if errorlevel 1 (
    echo Could not prepare matching PyTorch and TorchAudio builds.
    exit /b 1
)

echo Installing optional SenseVoice dependencies...
"%PYTHON%" -m pip install -r "%~dp0requirements-sensevoice.txt"

if errorlevel 1 (
    echo Could not install the optional SenseVoice dependencies.
    exit /b 1
)

echo Verifying installation...
"%PYTHON%" -c "import torch, torchaudio, funasr, modelscope; from funasr import AutoModel; print('torch=' + torch.__version__); print('torchaudio=' + torchaudio.__version__); print('cuda_available=' + str(torch.cuda.is_available())); print('device=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')); print('funasr=' + funasr.__version__); print('modelscope=' + modelscope.__version__)"

if errorlevel 1 (
    echo SenseVoice dependency verification failed.
    exit /b 1
)

echo SenseVoice dependencies installed successfully.
exit /b 0
