# Whisper.cpp files

Current Version 
- Whisper.cpp [Release 1.5.1](https://github.com/ggerganov/whisper.cpp/releases)

Whisper.cpp tends to have releases often. These files will need to be updated at some cadence.
We are mostly interested in performance improvements in main.exe so transcription speeds are faster with or without the use of GPU

- [main.exe](https://github.com/ggerganov/whisper.cpp/releases/download/v1.5.1/whisper-cublas-11.8.0-bin-x64.zip)
- [whisper.dll](https://github.com/ggerganov/whisper.cpp/releases/download/v1.5.1/whisper-cublas-11.8.0-bin-x64.zip)



## Whisper.cpp fixes we are waiting on

- [PR 1549](https://github.com/ggerganov/whisper.cpp/pull/1549)
  This will allow us to use whisper.cpp itself to convert wav files to 16 khz files instead of using ffmpeg for the same
- [PR 1524](https://github.com/ggerganov/whisper.cpp/pull/1524)
  This will allow us to use Python bindings for whisper.cpp instead of invoking main.exe process
