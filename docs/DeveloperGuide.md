## 🎬 Testing Transcribe Code changes

Unit Tests

```
python -m unittest discover --verbose .\tests
```

## Creating Windows installs

Install Winrar from https://www.win-rar.com/.

Required for generating binaries from python code. If you do not intend to generate binaries and are only writing python code, you do not need to install winrar. 

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

Note that installation files are generated every few weeks. So these file will almost always trail the latst codebase available in the repo.

1. Download the zip file from
```
https://drive.google.com/file/d/1Iy32YjDXK7Bga7amOUTA4Gx9VEoibPi-/view?usp=sharing
```
2. Unzip the files in a folder.

3. (Optional) Replace the Open API key in `parameters.yaml` file in the transcribe directory:

   Replace the Open API key in `parameters.yaml` file manually. Open in a text editor and alter the line:

      ```
        api_key: 'API_KEY'
      ```
      Replace "API KEY" with the actual OpenAI API key. Save the file.

4. Execute the file `transcribe\transcribe.exe\transcribe.exe`
