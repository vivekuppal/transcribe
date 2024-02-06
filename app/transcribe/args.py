import sys
import os
import argparse
from argparse import RawTextHelpFormatter
import yaml
from global_vars import TranscriptionGlobals
import interactions  # noqa: E402 pylint: disable=C0413
from tsutils import utilities, duration, configuration  # noqa: E402 pylint: disable=C0413
from sdk import audio_recorder as ar  # noqa: E402 pylint: disable=C0413


def create_args() -> argparse.Namespace:
    """Set up Command line arguments for application"""
    cmd_args = argparse.ArgumentParser(description='Command Line Arguments for Transcribe',
                                       formatter_class=RawTextHelpFormatter)
    cmd_args.add_argument('-a', '--api', action='store_true',
                          help='Use the online Open AI API for transcription.\
                          \nThis option requires an API KEY and will consume Open AI credits.')
    cmd_args.add_argument('-e', '--experimental', action='store_true',
                          help='Experimental command line argument. Behavior is undefined.')
    cmd_args.add_argument('-stt', '--speech_to_text', action='store', default='whisper',
                          choices=['whisper', 'whisper.cpp', 'deepgram'],
                          help='Specify the Speech to text Engine.'
                          '\nLocal STT models tend to perform best for response times.'
                          '\nAPI based STT models tend to perform best for accuracy.')
    cmd_args.add_argument('-c', '--chat-inference-provider', action='store', default='openai',
                          choices=['openai', 'together'],
                          help='Specify the Chat Inference engine.')
    cmd_args.add_argument('-k', '--api_key', action='store', default=None,
                          help='API Key for accessing OpenAI APIs. This is an optional parameter.\
                            \nWithout the API Key only transcription works.\
                            \nThis option will not save the API key anywhere, to persist the API'
                          ' key use the -sk option.')
    cmd_args.add_argument('-sk', '--save_api_key', action='store', default=None,
                          help='Save the API key for accessing OpenAI APIs to override.yaml file.\
                            \nSubsequent invocations of the program will not require API key on command line.\
                            \nTo not persist the API key use the -k option.')
    cmd_args.add_argument('-t', '--transcribe', action='store', default=None,
                          help='Transcribe the given audio file to generate text.\
                            \nThis option respects the -m (model) option.\
                            \nOutput is produced in transcription.txt or file specified using the -o option.')  # noqa: E501  pylint: disable=C0115
    cmd_args.add_argument('-o', '--output_file', action='store', default=None,
                          help='Generate output in this file.\
                            \nThis option is valid only for the -t (transcribe) option.')
    cmd_args.add_argument('-m', '--model', action='store', choices=[
        'tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large'],
        default='base',
        help='Specify the OpenAI Local Transcription model file to use.'
        '\nThe necessary model files will be downloaded once at run time.'
        '\n The files can also be manually downloaded from these locations.'
        '\ntiny multi-lingual model has to be downloaded from the link   '
        'https://drive.google.com/file/d/1M4AFutTmQROaE9xk2jPc5Y4oFRibHhEh/view?usp=drive_link'
        '\nbase english model has to be downloaded from the link         '
        'https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt'  # noqa: E501  pylint: disable=C0301
        '\nbase multi-lingual model has to be downloaded from the link   '
        'https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt'  # noqa: E501  pylint: disable=C0115
        '\nsmall english model has to be downloaded from the link        '
        'https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt'  # noqa: E501  pylint: disable=C0115
        '\nsmall multi-lingual model has to be downloaded from the link  '
        'https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt'  # noqa: E501  pylint: disable=C0115
        '\n\nThe models below require higher computing power: \n\n'
        '\nmedium english model has to be downloaded from the link       '
        'https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt'  # noqa: E501  pylint: disable=C0115
        '\nmedium multi-lingual model has to be downloaded from the link '
        'https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt'  # noqa: E501  pylint: disable=C0115
        '\nlarge model has to be downloaded from the link                '
        'https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt'  # noqa: E501  pylint: disable=C0115
        '\nlarge-v1 model has to be downloaded from the link             '
        'https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt'  # noqa: E501  pylint: disable=C0115
        '\nlarge-v2 model has to be downloaded from the link             '
        'https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt'  # noqa: E501  pylint: disable=C0115
        '\nlarge-v3 model has to be downloaded from the link             '
        'https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt')  # noqa: E501  pylint: disable=C0115
    cmd_args.add_argument('-l', '--list_devices', action='store_true',
                          help='List all audio drivers and audio devices on this machine.'
                          '\nUse this list index to select the microphone, speaker device for transcription.')
    cmd_args.add_argument('-mi', '--mic_device_index', action='store', default=None, type=int,
                          help='Device index of the microphone for capturing sound.'
                          '\nDevice index can be obtained using the -l option.')
    cmd_args.add_argument('-si', '--speaker_device_index', action='store', default=None, type=int,
                          help='Device index of the speaker for capturing sound.'
                          '\nDevice index can be obtained using the -l option.')
    cmd_args.add_argument('-dm', '--disable_mic', action='store_true',
                          help='Disable transcription from Microphone')
    cmd_args.add_argument('-ds', '--disable_speaker', action='store_true',
                          help='Disable transcription from Speaker')
    args = cmd_args.parse_args()
    return args


def handle_args_batch_tasks(args: argparse.Namespace, global_vars: TranscriptionGlobals):
    """Handle batch tasks, after which the program will exit."""
    interactions.params(args)

    if args.list_devices:
        print('\n\nList all audio drivers and devices on this machine')
        ar.print_detailed_audio_info()
        sys.exit(0)

    if args.save_api_key is not None:
        save_api_key(args)
        sys.exit(0)

    if args.transcribe is not None:
        with duration.Duration(name='Transcription', log=False, screen=True):
            output_file = args.output_file if args.output_file is not None else "transcription.txt"
            print(f'Converting the audio file {args.transcribe} to text.')
            print(f'{args.transcribe} file size '
                  f'{utilities.naturalsize(os.path.getsize(args.transcribe))}.')
            print(f'Text output will be produced in {output_file}.')
            # For whisper.cpp STT convert the file to 16 khz
            file_path = args.transcribe
            if args.speech_to_text == 'whisper.cpp':
                file_path = global_vars.transcriber.convert_wav_to_16khz_format(args.transcribe)

            results = global_vars.transcriber.stt_model.get_transcription(file_path)
            # process_response can be improved to make the output more palatable to human reading
            text = global_vars.transcriber.stt_model.process_response(results)
            if results is not None and len(text) > 0:
                with open(output_file, encoding='utf-8', mode='w') as f:
                    f.write(f"{text}\n")
                print('Complete!')
            else:
                print('Error during Transcription!')
                print(f'Please ensure {args.transcribe} is an audio file.')
                sys.exit(1)
        sys.exit(0)


def update_args_config(args: argparse.Namespace, config: dict):
    # Command line arg for api_key takes preference over api_key specified in yaml file
    # TODO: We should be able to set deepgram API key from command line as well
    if args.api_key is not None:
        config['OpenAI']['api_key'] = args.api_key

    if args.model is not None:
        config['OpenAI']['local_transcripton_model_file'] = args.model
        config['WhisperCpp']['local_transcripton_model_file'] = args.model
    else:
        config['OpenAI']['local_transcripton_model_file'] = 'base'
        config['WhisperCpp']['local_transcripton_model_file'] = 'base'

    if args.api:
        config['General']['use_api'] = args.api

    if args.disable_mic:
        config['General']['disable_mic'] = args.disable_mic

    if args.mic_device_index is not None:
        config['General']['mic_device_index'] = int(args.mic_device_index)

    if args.disable_speaker:
        config['General']['disable_speaker'] = args.disable_speaker

    if args.speaker_device_index is not None:
        config['General']['speaker_device_index'] = int(args.speaker_device_index)


def update_audio_devices(global_vars: TranscriptionGlobals, config: dict):
    """Handle all application configuration using the command line args"""

    # Handle mic if it is not disabled in arguments or yaml file
    if not config['General']['disable_mic']:
        if config['General']['mic_device_index'] != -1:
            print('[INFO] Override default microphone with device specified in parameters file.')
            global_vars.user_audio_recorder.set_device(index=int(config['General']['mic_device_index']))

    # Handle speaker if it is not disabled in arguments or yaml file
    if not config['General']['disable_speaker']:
        if config['General']['speaker_device_index'] != -1:
            print('[INFO] Override default speaker with device specified in parameters file.')
            global_vars.user_audio_recorder.set_device(index=int(config['General']['speaker_device_index']))


def save_api_key(args: argparse.Namespace):
    """Save the API key specified on command line to override parameters file"""

    yml = configuration.Config()
    with open(yml.config_override_file, mode='r', encoding='utf-8') as file:
        try:
            altered_config = yaml.load(stream=file, Loader=yaml.CLoader)
        except ImportError as err:
            print(f'Failed to load yaml file: {yml.config_override_file}.')
            print(f'Error: {err}')
            sys.exit(1)

    altered_config['OpenAI']['api_key'] = args.save_api_key
    yml.add_override_value(altered_config)
    print(f'Saved API Key to {yml.config_override_file}')
