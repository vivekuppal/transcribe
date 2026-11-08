python --version
python -m venv venv
call venv\scripts\activate.bat
python -m pip install --upgrade pip
cd app\transcribe
python -m pip install -r requirements.txt
python -m pip install pytest

echo.
echo Optional:
echo   app\transcribe\setup-gpu.bat             - local speech to text on an NVIDIA GPU
echo   app\transcribe\setup-openai-whisper.bat  - the original openai-whisper engine (needs PyTorch, several GB)
echo.
echo To Run transcribe, execute the following command
echo python main.py
