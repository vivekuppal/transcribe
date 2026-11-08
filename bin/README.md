# whisper.cpp (optional)

Only needed for `-stt whisper.cpp`. The standard local engine (faster-whisper) does not use it.

The old whisper.cpp 1.5.0 files (2023) that used to be here were removed: they were years behind
and needed extra CUDA files. To use whisper.cpp:

1. Open the latest release: https://github.com/ggml-org/whisper.cpp/releases
2. Download the Windows x64 build (there is a CPU build and a CUDA build for an NVIDIA GPU).
3. Put all of its files (the `.exe` and `.dll` files) into this `bin` folder, so that `bin\whisper-cli.exe` exists.

Transcribe looks for `whisper-cli.exe` (and, for older builds, `main.exe`) in this folder.
The model (`ggml-<name>.bin`) is downloaded by itself on first use.
