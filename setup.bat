python --version
python -m venv venv
call venv\scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install torch==2.11.0+cu126 torchaudio==2.11.0+cu126 --index-url https://download.pytorch.org/whl/cu126
cd app\transcribe
python -m pip install -r requirements.txt
python -m pip install pytest

echo To Run transcribe, execute the following command
echo python main.py
