import sys
import time
import atexit
import app_utils as au
from args import create_args, update_args_config, handle_args_batch_tasks
from global_vars import T_GLOBALS
from appui import AppUI
sys.path.append('../..')
from tsutils import configuration  # noqa: E402 pylint: disable=C0413
from tsutils import app_logging as al  # noqa: E402 pylint: disable=C0413
from tsutils import utilities as u  # noqa: E402 pylint: disable=C0413


def main():
    """Primary method to run transcribe
    """
    args = create_args()

    config = configuration.Config().data
    au.start_ffmpeg()

    # Initiate global variables
    global_vars = T_GLOBALS

    update_args_config(args, config)
    # Initiate DB
    au.initiate_db(global_vars)
    global_vars.initiate_audio_devices(config)
    au.create_transcriber(name=config['General']['stt'],
                          config=config,
                          api=bool(config['General']['use_api']),
                          global_vars=global_vars)
    global_vars.transcriber.set_source_properties(mic_source=global_vars.user_audio_recorder.source,
                                                  speaker_source=global_vars.speaker_audio_recorder.source)

    # Remove potential temp files from previous invocation
    data_dir = u.get_data_path(app_name='Transcribe')
    u.delete_files([
        f'{data_dir}/logs/speaker.wav',
        f'{data_dir}/logs/speaker.wav.bak',
        f'{data_dir}/logs/mic.wav',
        f'{data_dir}/logs/mic.wav.bak'])

    # Convert raw audio files to real wav file format when program exits
    atexit.register(au.shutdown, global_vars)

    user_stop_func = global_vars.user_audio_recorder.record_audio(global_vars.audio_queue)
    global_vars.user_audio_recorder.stop_record_func = user_stop_func

    time.sleep(2)

    speaker_stop_func = global_vars.speaker_audio_recorder.record_audio(global_vars.audio_queue)
    global_vars.speaker_audio_recorder.stop_record_func = speaker_stop_func

    # Transcriber needs to be created before handling batch tasks which include batch
    # transcription. This order of initialization results in initialization of Mic, Speaker
    # as well which is not necessary for some batch tasks.
    # This does not have any side effects.
    handle_args_batch_tasks(args, global_vars, config)

    # Initiate logging
    log_listener = al.initiate_log(config=config)

    aui = AppUI(config=config)
    au.initiate_app_threads(global_vars=global_vars, config=config)

    print("READY")

    # Set the response lang in STT Model.
    global_vars.transcriber.stt_model.set_lang(config['OpenAI']['audio_lang'])
    aui.update_initial_transcripts()
    aui.start()
    log_listener.stop()


if __name__ == "__main__":
    main()
