import sys
import os
import threading
import argparse
from argparse import RawTextHelpFormatter
import time
import subprocess
import yaml
import customtkinter as ctk
from AudioTranscriber import AudioTranscriber
from GPTResponder import GPTResponder
import AudioRecorder as ar
from audio_player import AudioPlayer
import TranscriberModels
import interactions
import ui
import GlobalVars
import configuration
import conversation
import app_logging
import utilities
import duration


def save_api_key(args: argparse.Namespace):
    """Save the API key specified on command line to override parameters file"""
    yml = configuration.Config()
    altered_config: dict = {'OpenAI': {'api_key': args.save_api_key}}
    yml.add_override_value(altered_config)
    # save override file to disk
    with open(file=yml.config_override_file, mode="w", encoding='utf-8') as file:
        yaml.dump(altered_config, file, default_flow_style=False)
    print(f'Saved API Key to {yml.config_override_file}')


def initiate_app_threads(global_vars: GlobalVars,
                         model: TranscriberModels.APIWhisperTranscriber | TranscriberModels.WhisperTranscriber):
    """Start all threads required for the application"""
    # Transcribe and Respond threads, both work on the same instance of the AudioTranscriber class
    global_vars.transcriber = AudioTranscriber(global_vars.user_audio_recorder.source,
                                               global_vars.speaker_audio_recorder.source,
                                               model,
                                               convo=global_vars.convo)
    global_vars.audio_player = AudioPlayer(convo=global_vars.convo)
    transcribe_thread = threading.Thread(target=global_vars.transcriber.transcribe_audio_queue,
                                         name='Transcribe',
                                         args=(global_vars.audio_queue,))
    transcribe_thread.daemon = True
    transcribe_thread.start()

    global_vars.responder = GPTResponder(convo=global_vars.convo)

    respond_thread = threading.Thread(target=global_vars.responder.respond_to_transcriber,
                                      name='Respond',
                                      args=(global_vars.transcriber,))
    respond_thread.daemon = True
    respond_thread.start()

    # Convert response from text to sound and play to user
    audio_response_thread = threading.Thread(target=global_vars.audio_player.play_audio_loop,
                                             name='AudioResponse')
    audio_response_thread.daemon = True
    audio_response_thread.start()

    # Periodically clear transcription data, if so configured
    clear_transcript_thread = threading.Thread(
        target=global_vars.transcriber.clear_transcript_data_loop,
        name='ClearTranscript',
        args=(global_vars.audio_queue,))

    clear_transcript_thread.daemon = True
    clear_transcript_thread.start()


def start_ffmpeg():
    """Start ffmpeg library"""
    try:
        subprocess.run(["ffmpeg", "-version"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       check=True)
    except FileNotFoundError:
        print("ERROR: The ffmpeg library is not installed. Please install \
              ffmpeg and try again.")
        sys.exit(1)


def create_args() -> argparse.Namespace:
    """Set up Command line arguments for application"""
    cmd_args = argparse.ArgumentParser(description='Command Line Arguments for Transcribe',
                                       formatter_class=RawTextHelpFormatter)
    cmd_args.add_argument('-a', '--api', action='store_true',
                          help='Use the online Open AI API for transcription.\
                          \nThis option requires an API KEY and will consume Open AI credits.')
    cmd_args.add_argument('-e', '--experimental', action='store_true',
                          help='Experimental command line argument. Behavior is undefined.')
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
                            \nOutput is produced in transcription.txt or file specified using the -o option.')
    cmd_args.add_argument('-o', '--output_file', action='store', default=None,
                          help='Generate output in this file.\
                            \nThis option is valid only for the -t (transcribe) option.')
    cmd_args.add_argument('-m', '--model', action='store', choices=[
        'tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large'],
        default='tiny',
        help='Specify the LLM to use for transcription.'
        '\nBy default tiny english model is part of the install.'
        '\ntiny multi-lingual model has to be downloaded from the link   '
        'https://drive.google.com/file/d/1M4AFutTmQROaE9xk2jPc5Y4oFRibHhEh/view?usp=drive_link'
        '\nbase english model has to be downloaded from the link         '
        'https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt'
        '\nbase multi-lingual model has to be downloaded from the link   '
        'https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt'
        '\nsmall english model has to be downloaded from the link        '
        'https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt'
        '\nsmall multi-lingual model has to be downloaded from the link  '
        'https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt'
        '\n\nThe models below require higher computing power: \n\n'
        '\nmedium english model has to be downloaded from the link       '
        'https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt'
        '\nmedium multi-lingual model has to be downloaded from the link '
        'https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt'
        '\nlarge model has to be downloaded from the link                '
        'https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt'
        '\nlarge-v1 model has to be downloaded from the link             '
        'https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt'
        '\nlarge-v2 model has to be downloaded from the link             '
        'https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt')
    cmd_args.add_argument('-l', '--list_devices', action='store_true',
                          help='List all audio drivers and audio devices on this machine. \
                            \nUse this list index to select the microphone, speaker device for transcription.')
    cmd_args.add_argument('-mi', '--mic_device_index', action='store', default=None, type=int,
                          help='Device index of the microphone for capturing sound.'
                          '\nDevice index can be obtained using the -l option.')
    cmd_args.add_argument('-si', '--speaker_device_index', action='store', default=None, type=int,
                          help='Device index of the speaker for capturing sound.'
                          '\nDevice index can be obtained using the -l option.')
    cmd_args.add_argument('-dm', '--disable_mic', action='store_true',
                          help='Enable transcription from Microphone')
    cmd_args.add_argument('-ds', '--disable_speaker', action='store_true',
                          help='Enable transcription from Speaker')
    args = cmd_args.parse_args()
    return args


def handle_args_batch_tasks(args: argparse.Namespace):
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
            model = TranscriberModels.get_model(args.api, model=args.model)
            print(f'Converting the audio file {args.transcribe} to text.')
            print(f'{args.transcribe} file size '
                  f'{utilities.naturalsize(os.path.getsize(args.transcribe))}.')
            print(f'Text output will be produced in {output_file}.')
            results = model.get_transcription(args.transcribe)
            if results is not None and len(results) > 0:
                with open(output_file, encoding='utf-8', mode='w') as f:
                    for segment in results['segments']:
                        f.write(f"{segment['start']} - {segment['end']}s: {segment['text']}\n")

                print('Complete!')
            else:
                print('Error during Transcription!')
                print('Please ensure {args.transcribe} is an audio file.')
                sys.exit(1)
        sys.exit(0)


def handle_args(args: argparse.Namespace, global_vars: GlobalVars, config: dict):
    """Handle all application configuration using the command line args"""
    if args.mic_device_index is not None:
        print('[INFO] Override default microphone with device specified on command line.')
        global_vars.user_audio_recorder.set_device(index=args.mic_device_index)

    if args.speaker_device_index is not None:
        print('[INFO] Override default speaker with device specified on command line.')
        global_vars.speaker_audio_recorder.set_device(index=args.speaker_device_index)

    # Command line arg for api_key takes preference over api_key specified in parameters.yaml file
    if args.api_key is not None:
        api_key: bool = args.api_key
    else:
        api_key: bool = config['OpenAI']['api_key']
    global_vars.api_key = api_key


def main():
    """Primary method to run transcribe
    """
    args = create_args()

    # Initiate config
    config = configuration.Config().data
    handle_args_batch_tasks(args)

    # Initiate global variables
    # Two calls to GlobalVars.TranscriptionGlobals is on purpose
    global_vars = GlobalVars.TranscriptionGlobals()

    global_vars = GlobalVars.TranscriptionGlobals(key=config["OpenAI"]["api_key"])

    # Initiate logging
    log_listener = app_logging.initiate_log(config=config)

    handle_args(args, global_vars, config)

    start_ffmpeg()

    model = TranscriberModels.get_model(args.api, model=args.model)

    root = ctk.CTk()
    ui_cb = ui.ui_callbacks()
    ui_components = ui.create_ui_components(root)
    transcript_textbox = ui_components[0]
    global_vars.response_textbox = ui_components[1]
    update_interval_slider = ui_components[2]
    update_interval_slider_label = ui_components[3]
    global_vars.freeze_button = ui_components[4]
    lang_combobox = ui_components[5]
    global_vars.filemenu = ui_components[6]
    response_now_button = ui_components[7]
    read_response_now_button = ui_components[8]
    global_vars.editmenu = ui_components[9]
    global_vars.user_audio_recorder.record_into_queue(global_vars.audio_queue)

    time.sleep(2)

    global_vars.speaker_audio_recorder.record_into_queue(global_vars.audio_queue)
    global_vars.freeze_state = [True]
    global_vars.convo = conversation.Conversation()

    # disable speaker/microphone on startup
    if args.disable_speaker:
        print('[INFO] Disabling Speaker')
        ui_cb.enable_disable_speaker(global_vars.editmenu)

    if args.disable_mic:
        print('[INFO] Disabling Microphone')
        ui_cb.enable_disable_microphone(global_vars.editmenu)

    initiate_app_threads(global_vars=global_vars, model=model)

    print("READY")

    root.grid_rowconfigure(0, weight=100)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=1)
    root.grid_rowconfigure(3, weight=1)
    root.grid_columnconfigure(0, weight=2)
    root.grid_columnconfigure(1, weight=1)

    global_vars.freeze_button.configure(command=ui_cb.freeze_unfreeze)
    response_now_button.configure(command=ui_cb.update_response_ui_now)
    read_response_now_button.configure(command=ui_cb.update_response_ui_and_read_now)
    label_text = f'Update Response interval: {update_interval_slider.get()} seconds'
    update_interval_slider_label.configure(text=label_text)
    lang_combobox.configure(command=model.change_lang)

    ui.update_transcript_ui(global_vars.transcriber, transcript_textbox)
    ui.update_response_ui(global_vars.responder, global_vars.response_textbox,
                          update_interval_slider_label, update_interval_slider,
                          global_vars.freeze_state)

    root.mainloop()
    log_listener.stop()


if __name__ == "__main__":
    main()
