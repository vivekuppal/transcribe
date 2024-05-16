import sys
import time
import atexit
import app_utils as au
import customtkinter as ctk
from args import create_args, update_args_config, handle_args_batch_tasks
from global_vars import T_GLOBALS
sys.path.append('../..')
import ui  # noqa: E402 pylint: disable=C0413
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
    u.delete_files(['speaker.wav', 'speaker.wav.bak', 'mic.wav', 'mic.wav.bak'])

    # Convert raw audio files to real wav file format when program exits
    # atexit.register(global_vars.user_audio_recorder.write_wav_data_to_file)
    # atexit.register(global_vars.speaker_audio_recorder.write_wav_data_to_file)
    atexit.register(au.shutdown, global_vars)

    user_stop_func = global_vars.user_audio_recorder.record_audio(global_vars.audio_queue)
    global_vars.user_audio_recorder.stop_record_func = user_stop_func

    time.sleep(2)

    speaker_stop_func = global_vars.speaker_audio_recorder.record_audio(global_vars.audio_queue)
    global_vars.speaker_audio_recorder.stop_record_func = speaker_stop_func

#    update_audio_devices(global_vars, config)

    # Transcriber needs to be created before handling batch tasks which include batch
    # transcription. This order of initialization results in initialization of Mic, Speaker
    # as well which is not necessary for some batch tasks.
    # This does not have any side effects.
    handle_args_batch_tasks(args, global_vars, config)

    # Initiate logging
    log_listener = al.initiate_log(config=config)

    root = ctk.CTk()
    T_GLOBALS.main_window = root
    ui_cb = ui.UICallbacks()
    ui_components = ui.create_ui_components(root, config=config)
    global_vars.transcript_textbox = ui_components[0]
    global_vars.response_textbox = ui_components[1]
    update_interval_slider = ui_components[2]
    global_vars.update_interval_slider_label = ui_components[3]
    global_vars.freeze_button = ui_components[4]
    audio_lang_combobox = ui_components[5]
    response_lang_combobox = ui_components[6]
    global_vars.filemenu = ui_components[7]
    response_now_button = ui_components[8]
    read_response_now_button = ui_components[9]
    global_vars.editmenu = ui_components[10]
    github_link = ui_components[11]
    issue_link = ui_components[12]
    summarize_button = ui_components[13]

    # disable speaker/microphone on startup
    if config['General']['disable_speaker']:
        print('[INFO] Disabling Speaker')
        ui_cb.enable_disable_speaker(global_vars.editmenu)

    if config['General']['disable_mic']:
        print('[INFO] Disabling Microphone')
        ui_cb.enable_disable_microphone(global_vars.editmenu)

    au.initiate_app_threads(global_vars=global_vars, config=config)

    print("READY")

    root.grid_rowconfigure(0, weight=100)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=1)
    root.grid_rowconfigure(3, weight=1)
    root.grid_columnconfigure(0, weight=2)
    root.grid_columnconfigure(1, weight=1)

    global_vars.freeze_button.configure(command=ui_cb.freeze_unfreeze)
    response_now_button.configure(command=ui_cb.get_response_now)
    read_response_now_button.configure(command=ui_cb.update_response_ui_and_read_now)
    summarize_button.configure(command=ui_cb.summarize)
    update_interval_slider.configure(command=ui_cb.update_interval_slider_label)
    label_text = f'LLM Response interval: {int(update_interval_slider.get())} seconds'
    global_vars.update_interval_slider_label.configure(text=label_text)
    audio_lang_combobox.configure(command=ui_cb.set_audio_language)
    response_lang_combobox.configure(command=ui_cb.set_response_language)
    # Set the response lang in STT Model.
    global_vars.transcriber.stt_model.set_lang(config['OpenAI']['audio_lang'])
    github_link.bind('<Button-1>', lambda e:
                     ui_cb.open_link('https://github.com/vivekuppal/transcribe?referer=desktop'))
    issue_link.bind('<Button-1>', lambda e: ui_cb.open_link(
        'https://github.com/vivekuppal/transcribe/issues/new?referer=desktop'))

    ui.update_transcript_ui(global_vars.transcriber, global_vars.transcript_textbox)
    ui.update_response_ui(global_vars.responder, global_vars.response_textbox,
                          global_vars.update_interval_slider_label, update_interval_slider)

    root.mainloop()
    log_listener.stop()


if __name__ == "__main__":
    main()
