import datetime
from deepgram import (
    DeepgramClient,
    FileSource,
    PrerecordedOptions)


# Create Deepgram API key at https://console.deepgram.com/signup?jump=keys
DEEPGRAM_API_KEY = '<API_KEY>'
# Path to a .wav file for transcription
PATH_TO_FILE = '<PATH_TO_WAV_FILE>'


def main():
    # Initializes the Deepgram SDK
    deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
    # Open the audio file
    print(f'{datetime.datetime.now()} - Start transcription')
    with open(PATH_TO_FILE, 'rb') as audio_file:
        buffer_data = audio_file.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(
        model="nova",
        smart_format=True,
        utterances=True,
        punctuate=True,
        diarize=True,
        detect_language=True)

    response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
    print(response.to_json(indent=4))
    print(f'{datetime.datetime.now()} - End transcription')


main()
