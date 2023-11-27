REM Define variables for different hard coded paths (Change everything to your local PATHs)
REM SET SOURCE_DIR=D:\Code\transcribe
REM SET OUTPUT_DIR=D:\Code\transcribe\output
REM SET LIBSITE_PACAGES_DIR=D:\Code\transcribe\.venv\Lib\site-packages
REM SET EXECUTABLE_NAME=transcribe.exe
REM SET ZIP_FILE_DIR=D:\Code\transcribe\transcribe.rar
REM SET ZIP_LOCATION=D:\Code\transcribe\output\dist\transcribe.exe
REM SET WINRAR=C:\Program Files\WinRAR\rar.exe

REM Define variables for different hard coded paths (Change everything to your local PATHs)
SET SOURCE_DIR=C:\git\transcribe-main
REM Contents of output dir are deleted at the end of the script
SET OUTPUT_DIR=C:\git\output
SET LIBSITE_PACAGES_DIR=C:\git\transcribe-main\venv\Lib\site-packages
SET EXECUTABLE_NAME=transcribe.exe
SET ZIP_FILE_DIR=C:\git\output\transcribe.rar
SET ZIP_LOCATION=C:\git\output\dist\transcribe.exe
SET WINRAR=C:\Program Files\WinRAR\rar.exe

REM pyinstaller --clean --noconfirm --specpath C:\\git\\output --distpath C:\\git\\output\dist -n transcribe.exe --log-level DEBUG --recursive-copy-metadata "openai-whisper" main.py

SET PYINSTALLER_DIST_PATH=%OUTPUT_DIR%\dist
SET PYINSTALLER_TEMP_PATH=%OUTPUT_DIR%\temp
ECHO %PYINSTALLER_DIST_PATH%

pyinstaller --clean --noconfirm --workpath %PYINSTALLER_TEMP_PATH% --specpath %OUTPUT_DIR% --distpath %PYINSTALLER_DIST_PATH% -n %EXECUTABLE_NAME% --log-level DEBUG main.py

REM generate version.txt file
git rev-parse --short HEAD > version.txt

SET ASSETS_DIR_SRC=%LIBSITE_PACAGES_DIR%\whisper\assets\
SET ASSETS_DIR_DEST=%PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\whisper\assets

REM ensure the appropriate directories exist
if not exist %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\whisper mkdir %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\whisper
if not exist %ASSETS_DIR_DEST% mkdir %ASSETS_DIR_DEST%
if not exist %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\models mkdir %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\models
if not exist %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\logs mkdir %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\logs
if not exist %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\bin mkdir %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\bin

REM Copy appropriate files to the dir
copy %SOURCE_DIR%\models\tiny.en.pt %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\models\tiny.en.pt
copy %SOURCE_DIR%\parameters.yaml %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\parameters.yaml
copy %SOURCE_DIR%\override.yaml %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\override.yaml
copy %SOURCE_DIR%\version.txt %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\version.txt
copy %ASSETS_DIR_SRC%\mel_filters.npz %ASSETS_DIR_DEST%
copy %ASSETS_DIR_SRC%\gpt2.tiktoken %ASSETS_DIR_DEST%
copy %SOURCE_DIR%\bin\main.exe %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\bin\main.exe
copy %SOURCE_DIR%\bin\whisper.dll %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\bin\whisper.dll

REM Code for zipping the final package
ECHO Zipping output files...
 "%WINRAR%" a -r -ep1 -df -ibck "%ZIP_FILE_DIR%" "%ZIP_LOCATION%" 
ECHO File Zipped at location %ZIP_FILE_DIR%

REM Remove the temp, dist folders
rmdir /S /Q %PYINSTALLER_DIST_PATH%
rmdir /S /Q %PYINSTALLER_TEMP_PATH%
