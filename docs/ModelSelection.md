# Model Selection #

Transcribe architecture has two primary components that require model selection
- Speech to Text
- LLM Responses

## Speech to Text
Speech to text aspect can be done locally or online using the Whisper API. The online option requires the use of `-api` option on command line.

### Local Speech to Text
Local Speech to Text requires model selection. By default the `tiny` model for English is used. This model is part of the downloaded source code. There are many more models available, though they vary by size and computing power required.

See the help of transcribe `python main.py -h` for further details on local transcription models.

```python
  -m {tiny,base,small,medium,large-v1,large-v2,large-v3,large}, --model {tiny,base,small,medium,large-v1,large-v2,large-v3,large}
                        Specify the LLM to use for transcription.
                        By default tiny english model is part of the install.
                        tiny multi-lingual model has to be downloaded from the link   https://drive.google.com/file/d/1M4AFutTmQROaE9xk2jPc5Y4oFRibHhEh/view?usp=drive_link
                        base english model has to be downloaded from the link         https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt
                        base multi-lingual model has to be downloaded from the link   https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt
                        small english model has to be downloaded from the link        https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt
                        small multi-lingual model has to be downloaded from the link  https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt

                        The models below require higher computing power:


                        medium english model has to be downloaded from the link       https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt
                        medium multi-lingual model has to be downloaded from the link https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt
                        large model has to be downloaded from the link                https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt
                        large-v1 model has to be downloaded from the link             https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt
                        large-v2 model has to be downloaded from the link             https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt
                        large-v3 model has to be downloaded from the link             https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt
```

### Online Speech to Text
Online Speech to Text option is enabled using `--api` option. This option does not require model selection as the appropriate model is selected by the API behind the scenes.

## LLM Responses
The quality, cost and speed of responses from LLM depends on the model chosen. Out of the box transcribe uses `gpt-3.5-turbo-0301` model as specified in parameters.yaml

```python
    ai_model: gpt-3.5-turbo-0301
```

The model can be changed by altering the config in `parameters.yaml` or `override.yaml` file. 

Details of all models for OpenAI are available at `https://platform.openai.com/docs/models/continuous-model-upgrades`
