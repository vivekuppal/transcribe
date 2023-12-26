import sys
import time
import app_utils as au
import customtkinter as ctk
from args import create_args, update_args_config, handle_args_batch_tasks
from global_vars import T_GLOBALS
sys.path.append('../..')
import ui  # noqa: E402 pylint: disable=C0413
from tsutils import configuration  # noqa: E402 pylint: disable=C0413
from tsutils import app_logging as al  # noqa: E402 pylint: disable=C0413


def main():
    """Primary method to run transcribe
    """
    args = create_args()

    config = configuration.Config().data

    au.start_ffmpeg()

    # Initiate global variables
    # Two calls to GlobalVars.TranscriptionGlobals is on purpose
    global_vars = T_GLOBALS

    update_args_config(args, config)
    global_vars.initiate_audio_devices(config)
    au.create_transcriber(name=args.speech_to_text,
                          config=config,
                          api=bool(config['General']['use_api']),
                          global_vars=global_vars)
    global_vars.transcriber.set_source_properties(global_vars.user_audio_recorder.source,
                                                  global_vars.speaker_audio_recorder.source)

    stop_func = global_vars.user_audio_recorder.record_into_queue(global_vars.audio_queue)
    global_vars.user_audio_recorder.stop_record_func = stop_func

    time.sleep(2)

    stop_func = global_vars.speaker_audio_recorder.record_into_queue(global_vars.audio_queue)
    global_vars.speaker_audio_recorder.stop_record_func = stop_func

#    update_audio_devices(global_vars, config)

    # Transcriber needs to be created before handling batch tasks which include batch
    # transcription. This order of initialization results in initialization of Mic, Speaker
    # as well which is not necessary for some batch tasks.
    # This does not have any side effects.
    handle_args_batch_tasks(args, global_vars)

    # Initiate logging
    log_listener = al.initiate_log(config=config)

    root = ctk.CTk()
    ui_cb = ui.UICallbacks()
    ui_components = ui.create_ui_components(root)
    transcript_textbox = ui_components[0]
    global_vars.response_textbox = ui_components[1]
    update_interval_slider = ui_components[2]
    global_vars.update_interval_slider_label = ui_components[3]
    global_vars.freeze_button = ui_components[4]
    lang_combobox = ui_components[5]
    global_vars.filemenu = ui_components[6]
    response_now_button = ui_components[7]
    read_response_now_button = ui_components[8]
    global_vars.editmenu = ui_components[9]
    github_link = ui_components[10]
    issue_link = ui_components[11]

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
    response_now_button.configure(command=ui_cb.update_response_ui_now)
    read_response_now_button.configure(command=ui_cb.update_response_ui_and_read_now)
    update_interval_slider.configure(command=ui_cb.update_interval_slider_label)
    label_text = f'LLM Response interval: {int(update_interval_slider.get())} seconds'
    global_vars.update_interval_slider_label.configure(text=label_text)
    lang_combobox.configure(command=global_vars.transcriber.stt_model.set_lang)
    github_link.bind('<Button-1>', lambda e: ui_cb.open_link('https://github.com/vivekuppal/transcribe?referer=desktop'))
    issue_link.bind('<Button-1>', lambda e: ui_cb.open_link('https://github.com/vivekuppal/transcribe/issues/new?referer=desktop'))

    ui.update_transcript_ui(global_vars.transcriber, transcript_textbox)
    ui.update_response_ui(global_vars.responder, global_vars.response_textbox,
                          global_vars.update_interval_slider_label, update_interval_slider)

    root.mainloop()
    log_listener.stop()


if __name__ == "__main__":
    main()
