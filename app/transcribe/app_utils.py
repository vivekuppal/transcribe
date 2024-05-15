import sys
import subprocess  # nosec
import threading
from global_vars import TranscriptionGlobals
from audio_player import AudioPlayer  # noqa: E402 pylint: disable=C0413
from gpt_responder import InferenceResponderFactory, InferenceEnum
from audio_transcriber import WhisperCPPTranscriber, WhisperTranscriber, DeepgramTranscriber
from db.app_db import AppDB
sys.path.append('../..')
import interactions  # noqa: E402 pylint: disable=C0413
from sdk import transcriber_models as tm  # noqa: E402 pylint: disable=C0413


def create_responder(provider_name: str, config, convo, save_to_file: bool,
                     response_file_name: str):
    """Creates a responder / Inference provider object based on input parameters
    """
    responder_factory = InferenceResponderFactory()

    if provider_name.lower() == 'openai':
        responder = responder_factory.get_responder_instance(provider=InferenceEnum.OPENAI,
                                                             config=config,
                                                             convo=convo,
                                                             save_to_file=save_to_file,
                                                             response_file_name=response_file_name)
    elif provider_name.lower() == 'together':
        responder = responder_factory.get_responder_instance(provider=InferenceEnum.TOGETHER,
                                                             config=config,
                                                             convo=convo,
                                                             save_to_file=save_to_file,
                                                             response_file_name=response_file_name)
    else:
        responder = None
    return responder


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
    chat = config['General']['chat_inference_provider']
    global_vars.responder = create_responder(provider_name=chat,
                                             config=config,
                                             convo=global_vars.convo,
                                             save_to_file=save_llm_response_to_file,
                                             response_file_name=llm_response_file)
    if global_vars.responder is None:
        print(f'FATAL: Could not create Chat Reponder for {chat}')
        sys.exit(1)
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
        subprocess.run(["ffmpeg", "-version"],  # nosec
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       check=True)
    except FileNotFoundError:
        print("ERROR: The ffmpeg library is not installed. Please install \
              ffmpeg and try again.")
        sys.exit(1)


def initiate_db(global_vars: TranscriptionGlobals):
    # Create the DB if it does not exist and then init connections to it
    adb = AppDB()
    adb.initialize_db(db_context=global_vars.db_context)
    # Do any application initialization activities
    adb.initialize_app()


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
            stt_model_config=stt_model_config)

        t = DeepgramTranscriber(
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
            stt_model_config=stt_model_config)
        t = WhisperCPPTranscriber(
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
            stt_model_config=stt_model_config)
        t = WhisperTranscriber(
            global_vars.user_audio_recorder.source,
            global_vars.speaker_audio_recorder.source,
            model,
            convo=global_vars.convo,
            config=config)
    elif name.lower() == 'whisper' and api:
        stt_model_config: dict = {
            'api_key': config['OpenAI']['api_key'],
            'timeout': config['OpenAI']['response_request_timeout_seconds']
        }
        model = model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.WHISPER_API,
            stt_model_config=stt_model_config)
        t = WhisperTranscriber(
            global_vars.user_audio_recorder.source,
            global_vars.speaker_audio_recorder.source,
            model,
            convo=global_vars.convo,
            config=config)
    else:
        raise ValueError(f'Unknown transcriber: {name}')
    global_vars.set_transcriber(t)


def shutdown(global_vars: TranscriptionGlobals):
    global_vars.user_audio_recorder.write_wav_data_to_file()
    global_vars.speaker_audio_recorder.write_wav_data_to_file()
    AppDB().shutdown_app()
