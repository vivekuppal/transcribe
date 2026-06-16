python --version
python -m venv venv
call venv\scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cu121
cd app\transcribe
python -m pip install -r requirements.txt
python -m pip install pytest

echo To Run transcribe, execute the following command
echo python main.py
