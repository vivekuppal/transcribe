REM Define variables for different hard coded paths
SET SOURCE_DIR=C:\git\transcribe
SET OUTPUT_DIR=C:\git\output
SET LIBSITE_PACAGES_DIR=C:\pyenv\transcribe\Lib\site-packages
SET EXECUTABLE_NAME=transcribe.exe
SET ZIP_FILE_NAME=transcribe.zip

REM pyinstaller --clean --noconfirm --specpath C:\\git\\output --distpath C:\\git\\output\dist -n transcribe.exe --log-level DEBUG --recursive-copy-metadata "openai-whisper" main.py

SET PYINSTALLER_DIST_PATH=%OUTPUT_DIR%\dist
SET PYINSTALLER_TEMP_PATH=%OUTPUT_DIR%\temp
ECHO %PYINSTALLER_DIST_PATH%

pyinstaller --clean --noconfirm --workpath %PYINSTALLER_TEMP_PATH% --specpath %OUTPUT_DIR% --distpath %PYINSTALLER_DIST_PATH% -n %EXECUTABLE_NAME% --log-level DEBUG main.py

SET ASSETS_DIR_SRC=%LIBSITE_PACAGES_DIR%\whisper\assets\
SET ASSETS_DIR_DEST=%PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\whisper\assets

REM ensure the appropriate directories exist
if not exist %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\whisper mkdir %PYINSTALLER_DIST_PATH%\%EXECUTABLE_NAME%\whisper
if not exist %ASSETS_DIR_DEST% mkdir %ASSETS_DIR_DEST%

REM Copy appropriate files to the dir
copy %SOURCE_DIR%\tiny.en.pt %OUTPUT_DIR%\dist\%EXECUTABLE_NAME%\tiny.en.pt
copy %ASSETS_DIR_SRC%\mel_filters.npz %ASSETS_DIR_DEST%
copy %ASSETS_DIR_SRC%\gpt2.tiktoken %ASSETS_DIR_DEST%

REM Code for zipping the final package
REM Need to add whisper manuallyy
