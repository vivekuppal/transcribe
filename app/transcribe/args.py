import sys
import os
import re
import argparse
from argparse import RawTextHelpFormatter
import yaml
from global_vars import TranscriptionGlobals
import interactions  # noqa: E402 pylint: disable=C0413
from tsutils import utilities, duration, configuration  # noqa: E402 pylint: disable=C0413
from sdk import audio_recorder as ar  # noqa: E402 pylint: disable=C0413
import openai


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
    cmd_args.add_argument('-vk', '--validate_api_key', action='store', default=None,
                          help='Validate that it is a valid functioning api_key.\
                           \nWithout the API Key only transcription works.')
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
        '\nThe necessary model files will be downloaded once at run time.')  # noqa: E501  pylint: disable=C0115
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


def handle_args_batch_tasks(args: argparse.Namespace, global_vars: TranscriptionGlobals, config: dict):
    """Handle batch tasks, after which the program will exit."""
    interactions.params(args)

    if args.list_devices:
        print('\n\nList all audio drivers and devices on this machine')
        ar.print_detailed_audio_info()
        sys.exit(0)

    if args.save_api_key is not None:
        save_api_key(args)
        sys.exit(0)

    if args.validate_api_key is not None:
        chat_inference_provider = config['General']['chat_inference_provider']
        if chat_inference_provider == 'openai':
            settings_section = 'OpenAI'
        elif chat_inference_provider == 'together':
            settings_section = 'Together'

        base_url = config[settings_section]['base_url']
        model = config[settings_section]['ai_model']

        if utilities.is_api_key_valid(api_key=args.validate_api_key, base_url=base_url, model=model):
            print('The api_key is valid')
            client = openai.OpenAI(api_key=args.validate_api_key, base_url=base_url)

            if base_url != 'https://api.together.xyz':
                models = utilities.get_available_models(client=client)
                print('Available models: ')
                for model in models:
                    print(f'    {model}')
            client.close()
        else:
            print('The api_key is not valid')
        sys.exit(0)

    if args.transcribe is not None:
        with duration.Duration(name='Transcription', log=False, screen=True):
            output_file = args.output_file if args.output_file is not None else "transcription.txt"
            safe_filename = re.sub('[^0-9a-zA-Z\.]+', '_', output_file)
            print(f'Converting the audio file {args.transcribe} to text.')
            print(f'{args.transcribe} file size '
                  f'{utilities.naturalsize(os.path.getsize(args.transcribe))}.')
            print(f'Text output will be produced in {safe_filename}.')
            # For whisper.cpp STT convert the file to 16 khz
            file_path = args.transcribe
            if args.speech_to_text == 'whisper.cpp':
                file_path = global_vars.transcriber.convert_wav_to_16khz_format(args.transcribe)

            results = global_vars.transcriber.stt_model.get_transcription(file_path)
            # process_response can be improved to make the output more palatable to human reading
            text = global_vars.transcriber.stt_model.process_response(results)
            if results is not None and len(text) > 0:
                with open(safe_filename, encoding='utf-8', mode='w') as f:
                    f.write(f"{text}\n")
                print('Complete!')
            else:
                print('Error during Transcription!')
                print(f'Please ensure {args.transcribe} is an audio file.')
                sys.exit(1)
        sys.exit(0)


def update_args_config(args: argparse.Namespace, config: dict):
    """Update internal configuration with any overrides specified as
    arguments
    """
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
            altered_config = yaml.load(stream=file, Loader=yaml.SafeLoader)
        except ImportError as err:
            print(f'Failed to load yaml file: {yml.config_override_file}.')
            print(f'Error: {err}')
            sys.exit(1)

    altered_config['OpenAI']['api_key'] = args.save_api_key
    yml.add_override_value(altered_config)
    print(f'Saved API Key to {yml.config_override_file}')
