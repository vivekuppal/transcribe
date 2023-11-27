# Whisper.cpp files

Current Version 
- Whisper.cpp [Release 1.5.0](https://github.com/ggerganov/whisper.cpp/releases/tag/v1.5.0)

Whisper.cpp tends to have releases often. These files will need to be updated at some cadence.
We are mostly interested in performance improvements in main.exe so transcription speeds are faster with or without the use of GPU

- [main.exe](https://github.com/ggerganov/whisper.cpp/releases/download/v1.5.0/whisper-cublas-bin-x64.zip)
- [whisper.dll](https://github.com/ggerganov/whisper.cpp/releases/download/v1.5.0/whisper-cublas-bin-x64.zip)

Whisper.cpp 1.5.1 introduces dependencies on specific version of cublas which will require shipping extra cublas files.

## Whisper.cpp fixes we are waiting on

- [PR 1549](https://github.com/ggerganov/whisper.cpp/pull/1549)
  This will allow us to use whisper.cpp itself to convert wav files to 16 khz files instead of using ffmpeg for the same
- [PR 1524](https://github.com/ggerganov/whisper.cpp/pull/1524)
  This will allow us to use Python bindings for whisper.cpp instead of invoking main.exe process
