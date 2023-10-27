import datetime
import json
from deepgram import Deepgram


DEEPGRAM_API_KEY = 'API_KEY'
PATH_TO_FILE = 'PATH_TO_WAV_FILE'


def main():
    # Initializes the Deepgram SDK
    deepgram = Deepgram(DEEPGRAM_API_KEY)
    # Open the audio file
    print(f'{datetime.datetime.now()} - Start transcription')
    with open(PATH_TO_FILE, 'rb') as audio:
        # ...or replace mimetype as appropriate
        source = {'buffer': audio, 'mimetype': 'audio/wav'}
        response = deepgram.transcription.sync_prerecorded(source, {'punctuate': True})
        print(json.dumps(response, indent=4))
    print(f'{datetime.datetime.now()} - End transcription')


main()
