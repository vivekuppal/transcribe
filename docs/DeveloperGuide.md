# Developer Guide #

## 🎬 Testing Code changes

Unit Tests

```
python -m unittest discover --verbose .\tests
```

## Security Scanning

Install bandit for security scanning

```
pip install bandit
```

Run bandit locally

```
cd app/transcribe

bandit -c ./build/bandit.yaml -r .

To find only high level vulnerabilities run this command
bandit -ll -c ./build/bandit.yaml -r .
```

Snyk scans are executed daily for code analysis

## Creating Windows installs

Install Winrar from https://www.win-rar.com/.

Winrar is required for generating binaries from python code. If you do not intend to generate binaries and are only writing python code, you do not need to install winrar. 

Install pyInstaller

```
pip install pyinstaller==6.3.0
```

In the file ```generate_binary.bat``` replace these paths at the top of the file to paths specific to your machine. 

```
SET SOURCE_DIR=D:\Code\transcribe  
SET OUTPUT_DIR=D:\Code\transcribe\output
SET LIBSITE_PACAGES_DIR=D:\Code\transcribe\venv\Lib\site-packages
SET EXECUTABLE_NAME=transcribe.exe
SET ZIP_FILE_DIR=D:\Code\transcribe\transcribe.rar
SET WINRAR=C:\Program Files\WinRAR\winRAR.exe
```

Run ```generate_binary.bat``` file by replacing paths at the top of the file to the ones in your local machine. It should generate a zip file with everything compiled. To run the program simply go to zip file > transcribe.exe.

## Software Installation

Note that installation files are generated every few weeks. So these file will almost always trail the latest codebase available in the repo.
Latest Binary
- Generated: 2023-11-17
- Git version: 705fc86

1. Download the zip file from
```
https://drive.google.com/file/d/1TtdEkzQyxA8UaXV7rk9LGDTxMtWetjJa/view?usp=drive_link
```
2. Unzip the files in a folder.

3. (Optional) Replace the Open API key in `parameters.yaml` or `override.yaml` file in the transcribe directory:

   Replace the Open API key in `parameters.yaml` file manually. Open in a text editor and alter the line:

      ```
        api_key: 'API_KEY'
      ```
      Replace "API_KEY" with the actual OpenAI API key. Save the file.

4. Execute the file `transcribe\transcribe.exe\transcribe.exe`
