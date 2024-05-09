<img src="assets/Transcribe-2.png" width="100">


We are here to help. File [issues](https://github.com/vivekuppal/transcribe/issues) for any problems and we will resolve them.

## Source Code Install Video

Thanks to [Fahd Mirza](https://www.fahdmirza.com/) for the [installation video](https://www.youtube.com/watch?v=RX86zKdCpMc) for Transcribe.
Subscribe to his [Youtube channel](https://www.youtube.com/@fahdmirza) and read his [blog](https://www.fahdmirza.com/).

<a href="https://www.youtube.com/watch?feature=player_embedded&v=RX86zKdCpMc" target="_blank">
 <img src="https://img.youtube.com/vi/RX86zKdCpMc/0.jpg" alt="Watch the video" width="240" height="180"/>
</a>

# 👂🏻️ Transcribe ✍🏼️

[Join the community](https://transcribe-workspace.slack.com/channels/general)
Share your email in an issue to receive the invite to the community channel.

Transcribe provides real time transcription for microphone and speaker output. It generates a suggested conversation response using OpenAI's GPT API relevant to the current conversation.

## Why Transcribe over other Speech to Text apps ##
- Use Most of the functionality for **FREE**
- Multi Lingual support
- Choose between GPT 4.0, 3.5 or other inference models from OpenAI, or a plethora of inference models from [Together](https://docs.together.ai/docs/inference-models)
- Streaming fast LLM responses instead of waiting for a complete response
- Upto date with the latest OpenAI libraries
- Get LLM responses for selected text
- Install and use without python or other dependencies
- Security Features
- Choose Audio Inputs (Speaker or Mic or Both)
- Speech to Text
    - Offline - FREE
    - Online - paid
      - OpenAI Whisper - **(Encouraged)**
      - Deepgram
- Chat Inference Engines
    - OpenAI
    - Together
    - Perplexity
    - Azure hosted OpenAI - Some users have reported requiring code changes to make Azure work. Feedback appreciated.
- Conversation Summary
- Prompt customization
- Save chat history
- Response Audio

## Response Generation ##
Response generation requires a paid account with an OpenAI API key. **Encouraged**
or Deepgram
or Together ($25 free Credits)
oa Azure

OpenAI gpt-4 model provides the best response generation capabilities. Earlier models work ok, but can sometimes provide inaccurate answers if there is not enough conversation content at the beginning.
Together provides a large selection of [Inference models](https://docs.together.ai/docs/inference-models). Any of these can be used by making changes to `override.yaml` file.

When using OpenAI, without the OpenAI key, using continuous response or any action that requires interaction with the online LLM gives an error similar to below

```
Error when attempting to get a response from LLM.
Error code: 401 - {'error': {'message': 'Incorrect API key provided: API_KEY. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'param': None, 'code': 'invalid_api_key'}}
```

With a valid OpenAI key and no available credits, using continuous response gives an error similar to below
```
Error when attempting to get a response from LLM. Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs: https://platform.openai.com/docs/guides/error-codes/api-errors.', 'type': 'insufficient_quota', 'param': None, 'code': 'insufficient_quota'}} 
```


## ![Alt text](assets/on-demand-service-48.png) On Demand Features ![Alt text](assets/on-demand-service-48.png) ##
We develop mutually beneficial features on demand.

Create an issue in the repo to request mutually beneficial on demand features.

Connect on LinkedIn to discuss further.


## Features ##
- [Multilingual support](./docs/Multilingual.md)
- [Response Customization](./docs/ResponseCustomization.md)
- [Audio Customization](./docs/AudioCustomization.md)
- [Response for selected text](./docs/SelectedResponse.md)
- [Speech Mode](./docs/SpeechMode.md)
- [Save Content](./docs/SaveContent.md)
- [Model Selection](./docs/ModelSelection.md)
- [Batch Operations](./docs/BatchOperations.md)
- [Application Configuration](./docs/AppConfig.md)
- [OpenAI API Compatible Provider Support](./docs/Providers.md)


## Security ##
- <b>Secret scanning</b>: Continuous Integration with [GitGuardian](https://www.gitguardian.com/)
- <b>Static Code Analysis</b>: Regular static code scan scan with [Bandit](https://bandit.readthedocs.io/en/latest/)
- <b>Static Code Analysis</b>: Incorporate Snyk for daily static analysis of code
- <b>Secure Transmission</b>: All secure communications for any network communications
- <b>Dependency Security</b>: All strictest security features enabled in the Github repo


## Developer Guide ##
[Developer Guide](./docs/DeveloperGuide.md)


## Software Installation

Note that installation files are generated every few weeks. Generated binaries will almost always trail the latest codebase available in the repo.

Latest Binary
- Generated: 2024-01-30
- Git version: bbe1f4

1. Install ffmpeg

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

2. Download the zip file from
```
https://drive.google.com/file/d/1vJCHv8eEjp6q7HEnCMY5mlX_8Ys2_06u/view?usp=drive_link


Using GPU provides 2-3 times faster reseponse time depending on processing power of GPU.
```
3. Unzip the files in a folder.

4. (Optional) Add Open API key in `override.yaml` file in the transcribe directory:

   Create an [OpenAI account](https://openai.com/) or account from another provider

   Add OpenAI API key in `override.yaml` file manually. Open in a text editor and add these lines:

```
OpenAI:
   api_key: 'API_KEY'
```

   Replace "API_KEY" with the actual OpenAI API key. Save the file.

5. Execute the file `transcribe\transcribe.exe\transcribe.exe`



## 🆕 Best Performance with GPU 🥇
Application performs best with GPU support.

Make sure you have installed CUDA libraries if you have GPU: https://developer.nvidia.com/cuda-downloads

Application will automatically detect and use GPU once CUDA libraries are installed.

## 🆕 Getting Started 🥇

Follow below steps to run transcribe on your local machine.

### 📋 Prerequisites

- Python >=3.11.0
- (Optional) An OpenAI API key (set up a paid [OpenAI account](https://platform.openai.com/))
- Windows OS (Not tested on others)
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

2. Run setup file

   ```
   setup.bat
   ```

3. (Optional) Provide OpenAI API key in `override.yaml` file in the transcribe directory:

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

Upon initiation, Transcribe will begin transcribing microphone input and speaker output in real-time, optionally generating a suggested response based on the conversation. It is suggested to use continuous response feature after 1-2 minutes, once there is enough content in transcription window to provide enough context to the LLM.


## 👤 License 📖
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributions 🤝

Contributions are welcome! Open issues or submit pull requests to improve Transcribe.

## Videos
- [Install Video](https://www.youtube.com/watch?v=RX86zKdCpMc) Thanks to Fahd Mirza.
- [Fireside chat](https://www.youtube.com/watch?v=vUm-elVkxOI) for Transcribe.
