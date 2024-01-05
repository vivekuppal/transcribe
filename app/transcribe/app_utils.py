import sys
import subprocess
import threading
from global_vars import TranscriptionGlobals
from audio_player import AudioPlayer  # noqa: E402 pylint: disable=C0413
from gpt_responder import GPTResponder
from audio_transcriber import WhisperCPPTranscriber, WhisperTranscriber, DeepgramTranscriber
sys.path.append('../..')
import interactions  # noqa: E402 pylint: disable=C0413
from sdk import transcriber_models as tm  # noqa: E402 pylint: disable=C0413


def initiate_app_threads(global_vars: TranscriptionGlobals,
                         config: dict):
    """Start all threads required for the application"""
    # Transcribe and Respond threads, both work on the same instance of the AudioTranscriber class
    global_vars.audio_player_var = AudioPlayer(convo=global_vars.convo)
    transcribe_thread = threading.Thread(target=global_vars.transcriber.transcribe_audio_queue,
                                         name='Transcribe',
                                         args=(global_vars.audio_queue,))
    transcribe_thread.daemon = True
    transcribe_thread.start()

    save_llm_response_to_file: bool = config['General']['save_llm_response_to_file']
    llm_response_file = config['General']['llm_response_file']
    global_vars.responder = GPTResponder(config=config,
                                         convo=global_vars.convo,
                                         save_to_file=save_llm_response_to_file,
                                         file_name=llm_response_file)
    global_vars.responder.enabled = bool(config['General']['continuous_response'])

    respond_thread = threading.Thread(target=global_vars.responder.respond_to_transcriber,
                                      name='Respond',
                                      args=(global_vars.transcriber,))
    respond_thread.daemon = True
    respond_thread.start()

    # Convert response from text to sound and play to user
    audio_response_thread = threading.Thread(target=global_vars.audio_player_var.play_audio_loop,
                                             name='AudioResponse')
    audio_response_thread.daemon = True
    audio_response_thread.start()

    # Host config
    hc = interactions.HostConfig()
    host_config_thread = threading.Thread(target=hc.host_config_loop,
                                          name='HostConfig')
    host_config_thread.daemon = True
    host_config_thread.start()

    # Periodically clear transcription data, if so configured
    clear_transcript_thread = threading.Thread(
        target=global_vars.transcriber.clear_transcript_data_loop,
        name='ClearTranscript',
        args=(global_vars.audio_queue,))

    clear_transcript_thread.daemon = True
    clear_transcript_thread.start()

    # work_queue thread
    work_queue_thread = threading.Thread(
        target=global_vars.task_worker.task_exec_thread,
        name='WorkQueue'
    )
    work_queue_thread.daemon = True
    work_queue_thread.start()


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


def create_transcriber(
        name: str,
        config: dict,
        api: bool,
        global_vars: TranscriptionGlobals):
    """Creates a transcriber object based on input parameters
    """
    model_factory = tm.STTModelFactory()

    if name.lower() == 'deepgram':
        stt_model_config: dict = {
            'api_key': config['Deepgram']['api_key']
        }
        model = model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.DEEPGRAM_API,
            config=stt_model_config)
        global_vars.transcriber = DeepgramTranscriber(
            global_vars.user_audio_recorder.source,
            global_vars.speaker_audio_recorder.source,
            model,
            convo=global_vars.convo,
            config=config)
    elif name.lower() == 'whisper.cpp':
        stt_model_config: dict = {
            'local_transcripton_model_file': 'ggml-' + config['WhisperCpp']['local_transcripton_model_file'],
        }
        model = model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.WHISPER_CPP,
            config=stt_model_config)
        global_vars.transcriber = WhisperCPPTranscriber(
            global_vars.user_audio_recorder.source,
            global_vars.speaker_audio_recorder.source,
            model,
            convo=global_vars.convo,
            config=config)
    elif name.lower() == 'whisper' and not api:
        stt_model_config: dict = {
            'api_key': config['OpenAI']['api_key'],
            'local_transcripton_model_file': config['OpenAI']['local_transcripton_model_file'],
        }
        model = model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.WHISPER_LOCAL,
            config=stt_model_config)
        global_vars.transcriber = WhisperTranscriber(
            global_vars.user_audio_recorder.source,
            global_vars.speaker_audio_recorder.source,
            model,
            convo=global_vars.convo,
            config=config)
    elif name.lower() == 'whisper' and api:
        stt_model_config: dict = {
            'api_key': config['OpenAI']['api_key']
        }
        model = model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.WHISPER_API,
            config=stt_model_config)
        global_vars.transcriber = WhisperTranscriber(
            global_vars.user_audio_recorder.source,
            global_vars.speaker_audio_recorder.source,
            model,
            convo=global_vars.convo,
            config=config)
    else:
        raise ValueError(f'Unknown transcriber: {name}')
