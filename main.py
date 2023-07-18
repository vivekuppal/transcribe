import threading
import argparse
from argparse import RawTextHelpFormatter
import time
import requests
from requests.exceptions import ConnectionError
from AudioTranscriber import AudioTranscriber
from GPTResponder import GPTResponder
import customtkinter as ctk
import TranscriberModels
import subprocess
import interactions
import ui
from language import LANGUAGES_DICT
import globals


def main():
    # Set up all arguments
    cmd_args = argparse.ArgumentParser(description='Command Line Arguments for Transcribe',
                                       formatter_class=RawTextHelpFormatter)
    cmd_args.add_argument('-a', '--api', action='store_true',
                          help='Use the online Open AI API for transcription.\
                          \nThis option requires an API KEY and will consume Open AI credits.')
    cmd_args.add_argument('-m', '--model', action='store', choices=['tiny', 'base', 'small'],
                          default='tiny',
                          help='Specify the model to use for transcription.'
                          '\nBy default tiny english model is part of the install.'
                          '\ntiny multi-lingual model has to be downloaded from the link \
                            https://drive.google.com/file/d/1M4AFutTmQROaE9xk2jPc5Y4oFRibHhEh/view?usp=drive_link'
                          '\nbase english model has to be downloaded from the link \
                            https://drive.google.com/file/d/1E44DVjpfZX8tSrSagaDJXU91caZOkwa6/view?usp=drive_link'
                          '\nbase multi-lingual model has to be downloaded from the link \
                            https://drive.google.com/file/d/1UcqU_D0cPFqq_nckSfstMBfogFsvR-KR/view?usp=drive_link'
                          '\nsmall english model has to be downloaded from the link \
                            https://drive.google.com/file/d/1vhtoZCwfYGi5C4jK1r-QVr5GobSBnKiH/view?usp=drive_link'
                          '\nsmall multi-lingual model has to be downloaded from the link \
                            https://drive.google.com/file/d/1bl8er_st8WPZKPWVeYMNlaUi9IzR3jEZ/view?usp=drive_link'
                          '\nOpenAI has more models besides the ones specified above.'
                          '\nThose models are prohibitive to use on local machines because \
                            of memory requirements.')
    cmd_args.add_argument('-e', '--experimental', action='store_true', help='Experimental command\
                          line argument. Behavior is undefined.')
    args = cmd_args.parse_args()

    try:
        subprocess.run(["ffmpeg", "-version"],
                       stdout = subprocess.DEVNULL,
                       stderr = subprocess.DEVNULL)
    except FileNotFoundError:
        print("ERROR: The ffmpeg library is not installed. Please install \
              ffmpeg and try again.")
        return

    query_params = interactions.create_params()
    try:
        response = requests.get("http://127.0.0.1:5000/ping", params=query_params)
        if response.status_code != 200:
            print(f'Error received: {response}')
    except ConnectionError:
        print('Operating as a standalone client')

    global_vars = globals.TranscriptionGlobals()
    model = TranscriberModels.get_model(args.api, model=args.model)

    root = ctk.CTk()
    ui_components = ui.create_ui_components(root)
    transcript_textbox = ui_components[0]
    response_textbox = ui_components[1]
    update_interval_slider = ui_components[2]
    update_interval_slider_label = ui_components[3]
    global_vars.freeze_button = ui_components[4]
    lang_combobox = ui_components[5]

    global_vars.user_audio_recorder.record_into_queue(global_vars.audio_queue)

    time.sleep(2)

    global_vars.speaker_audio_recorder.record_into_queue(global_vars.audio_queue)

    # Transcribe and Respond threads, both work on the same instance of the AudioTranscriber class
    global_vars.transcriber = AudioTranscriber(global_vars.user_audio_recorder.source,
                                               global_vars.speaker_audio_recorder.source, model)
    transcribe_thread = threading.Thread(target=global_vars.transcriber.transcribe_audio_queue,
                                         args=(global_vars.audio_queue,))
    transcribe_thread.daemon = True
    transcribe_thread.start()

    global_vars.responder = GPTResponder()

    respond_thread = threading.Thread(target=global_vars.responder.respond_to_transcriber,
                                      args=(global_vars.transcriber,))
    respond_thread.daemon = True
    respond_thread.start()

    print("READY")

    root.grid_rowconfigure(0, weight=100)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=1)
    root.grid_rowconfigure(3, weight=1)
    root.grid_columnconfigure(0, weight=2)
    root.grid_columnconfigure(1, weight=1)

    # Add the clear transcript button to the UI
    # clear_transcript_button = ctk.CTkButton(root, text="Clear Audio Transcript",
    #                                        command=lambda: ui.clear_transcriber_context(global_vars.transcriber, global_vars.audio_queue))
    # clear_transcript_button.grid(row=1, column=0, padx=10, pady=3, sticky="nsew")

    global_vars.freeze_state = [True]

    ui_cb = ui.ui_callbacks()
    global_vars.freeze_button.configure(command=ui_cb.freeze_unfreeze)
    # copy_button.configure(command=ui_cb.copy_to_clipboard)
    # save_file_button.configure(command=ui_cb.save_file)
    # global_vars.transcript_button.configure(command=ui_cb.set_transcript_state)
    update_interval_slider_label.configure(text=f"Update interval: \
                                          {update_interval_slider.get()} \
                                          seconds")

    lang_combobox.configure(command=model.change_lang)

    ui.update_transcript_ui(global_vars.transcriber, transcript_textbox)
    ui.update_response_ui(global_vars.responder, response_textbox, update_interval_slider_label,
                          update_interval_slider, global_vars.freeze_state)

    root.mainloop()


if __name__ == "__main__":
    main()
