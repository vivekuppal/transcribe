@echo off
rem Optional: lets the local speech to text (faster-whisper) use an NVIDIA GPU.
rem Installs the CUDA 12 cuBLAS and cuDNN 9 libraries into the virtual environment
rem (no separate CUDA installation is needed). Without them the CPU is used.

set "PYTHON=%~dp0..\..\venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Transcribe virtual environment not found. Run setup.bat first.
    exit /b 1
)

echo Installing the NVIDIA libraries for faster-whisper...
"%PYTHON%" -m pip install -r "%~dp0requirements-gpu.txt"
if errorlevel 1 (
    echo Could not install the NVIDIA libraries.
    exit /b 1
)

echo Checking the GPU...
"%PYTHON%" -c "import sys; sys.path.insert(0, r'%~dp0..\..'); from sdk.transcriber_models import gpu_check; sys.exit(gpu_check())"
set "RESULT=%errorlevel%"
if "%RESULT%"=="0" (
    echo The GPU will be used for local speech to text.
    exit /b 0
)
if "%RESULT%"=="2" (
    echo No NVIDIA GPU was found. The CPU will be used.
    exit /b 0
)
echo The GPU libraries could not be loaded. The CPU will be used.
exit /b 1
