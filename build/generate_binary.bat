@echo off
rem Builds the Windows package (dist\Transcribe and dist\Transcribe-<version>-windows.zip).
rem Run from the repository folder after setup.bat:  build\generate_binary.bat 1.2.0
call venv\Scripts\activate.bat
python -m pip install pyinstaller
python build\build.py --version %1
