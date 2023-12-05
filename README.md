
A million thanks to Fahd Mirza for creating an [installation video](https://www.youtube.com/watch?v=RX86zKdCpMc) for Transcribe.
Please subscribe to his [youtube channel](https://www.youtube.com/@fahdmirza) and read his [blog](https://www.fahdmirza.com/).

[![install video](https://img.youtube.com/vi/RX86zKdCpMc/0.jpg)](https://www.youtube.com/watch?v=RX86zKdCpMc)

# 👂🏻️ Transcribe ✍🏼️

Transcribe provides real time transcription for microphone and speaker output. It generates a suggested conversation response using OpenAI's GPT API relevant to the current conversation.

![Screenshot](assets/Screenshot.png)

## Why Transcribe over ecoute ##
- Use Most of the functionality for FREE
- Choose between GPT 3.5, 4.0 or other models from OpenAI
- Install without python dependencies
- Speech to Text
    - Offline - FREE
    - Online - paid - OpenAI Whisper or Deepgram
- Prompt customization
- Manage Audio Input (Speaker or Mic or Both)
- Save chat history
- Response Audio

## ![Alt text](assets/on-demand-service-48.png) On Demand Features ![Alt text](assets/on-demand-service-48.png) ##
We develop mutually beneficial features on demand.

Create an issue in the repo to request on demand features.

## Features ##
- [Response Customization](./docs/ResponseCustomization.md)
- [Audio Customization](./docs/AudioCustomization.md)
- [Speech Mode](./docs/SpeechMode.md)
- [Save Content](./docs/SaveContent.md)
- [Model Selection](./docs/ModelSelection.md)
- [Batch Operations](./docs/BatchOperations.md)
- [Application Configuration](./docs/AppConfig.md)

## Developer Guide ##
[Developer Guide](./docs/DeveloperGuide.md)


## Software Installation

Note that installation files are generated every few weeks. So these file will almost always trail the latest codebase available in the repo.

Latest Binary
- Generated: 2023-11-23
- Git version: 705fc86

1. Download the zip file from
```
https://drive.google.com/file/d/1nCNAG9LpCZ7e1sTeC4rvRcF0WMp51_Fg/view?usp=sharing
```
2. Unzip the files in a folder.

3. (Optional) Add Open API key in `override.yaml` file in the transcribe directory:

   Add Open API key in `override.yaml` file manually. Open in a text editor and add these lines:

```
OpenAI:
   api_key: 'API_KEY'
```

   Replace "API_KEY" with the actual OpenAI API key. Save the file.

4. Execute the file `transcribe\transcribe.exe\transcribe.exe`

## 🆕 Best Performance with GPU 🥇
Application performs best with GPU support.

Make sure you have installed CUDA libraries if you have GPU: https://developer.nvidia.com/cuda-downloads

Application will automatically detect and use GPU once CUDA libraries are installed.

## 🆕 Getting Started 🥇

Follow below steps to run transcribe on your local machine.

### 📋 Prerequisites

- Python >=3.11.0
- (Optional) An OpenAI API key (set up a paid [OpenAI account](https://platform.openai.com/))
- Windows OS (Not tested on others as yet)
- FFmpeg

Steps to install FFmpeg on your system.

First, install Chocolatey, a package manager for Windows.

Open PowerShell as Administrator and run the following command:
```
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```
Once Chocolatey is installed, install FFmpeg by running the following command in PowerShell:
```
choco install ffmpeg
```
Run these commands in a PowerShell window with administrator privileges. For any issues during the installation, visit the official [Chocolatey](https://chocolatey.org/) and [FFmpeg](https://ffmpeg.org/) websites for troubleshooting.

### 🔧 Code Installation

1. Clone transcribe repository:

   ```
   git clone https://github.com/vivekuppal/transcribe
   ```

2. Navigate to `app\transcribe` folder:

   ```
   cd app\transcribe
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```
   
   It is recommended to create a virtual environment for installing the required packages
   
4. (Optional) Provide OpenAI API key in `override.yaml` file in the transcribe directory:

   Create the following section in `override.yaml` file
   ```yaml
   OpenAI:
     api_key: 'API_KEY'
   ```
   Alter the line:
   
      ```
        api_key: 'API_KEY'
      ```
      Replace "API_KEY" with the actual OpenAI API key. Save the file.


### 🎬 Running Transcribe

Run the main script from `app\transcribe\` folder:

```
python main.py
```

For a better version that also transcribes many non English languages, use:

```
python main.py --api
```

Upon initiation, Transcribe will begin transcribing microphone input and speaker output in real-time, optionally generating a suggested response based on the conversation. It is suggested to use continuous response feature after 1-2 minutes, once there is enough content in transcription window to provide enough context to the LLM.

The --api flag uses the online whisper api for transcription. This can significantly enhance transcription  accuracy, and it works in many languages (rather than just English). However, using the Whisper API consumes OpenAI credits and local transcription does not consume credits. This increased cost is attributed to the advanced features and capabilities that Whisper API provides. Despite the additional expense, the substantial improvements in speed and transcription accuracy may make it a worthwhile for your use case.

## ⚡️ Limitations ⚡️

While Transcribe provides real-time transcription and optional response suggestions, there are several known limitations to its functionality to be aware of:

**OpenAI Account**: If a paid OpenAI account with a valid Open API Key is not used, the command window displays the following error message repeatedly, though the application behvaior is not impacted in any way.
```
Incorrect API key provided: API_KEY. You can find your API key at https://platform.openai.com/account/api-keys.
```

## 👤 License 📖
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributions 🤝

Contributions are welcome! Open issues or submit pull requests to improve Transcribe.
