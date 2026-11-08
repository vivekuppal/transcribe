@echo off
rem Optional: installs the original openai-whisper engine and PyTorch (several GB).
rem Not needed for local speech to text: faster-whisper (installed by setup.bat) does the
rem same job faster. After installing, set in override.yaml:
rem   General:
rem     local_engine: openai-whisper
rem Use "setup-openai-whisper.bat --cuda" for the NVIDIA GPU build of PyTorch.

set "PYTHON=%~dp0..\..\venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Transcribe virtual environment not found. Run setup.bat first.
    exit /b 1
)

set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"
if /i "%~1"=="--cuda" set "TORCH_INDEX=https://download.pytorch.org/whl/cu126"

echo Installing PyTorch from %TORCH_INDEX% ...
"%PYTHON%" -m pip install torch --index-url "%TORCH_INDEX%"
if errorlevel 1 (
    echo Could not install PyTorch.
    exit /b 1
)

echo Installing openai-whisper...
"%PYTHON%" -m pip install -r "%~dp0requirements-openai-whisper.txt"
if errorlevel 1 (
    echo Could not install openai-whisper.
    exit /b 1
)

echo openai-whisper is installed. Set local_engine: openai-whisper in override.yaml to use it.
exit /b 0
