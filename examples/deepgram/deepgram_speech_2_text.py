import datetime
import json
from deepgram import Deepgram

# Create Deepgram API key at https://console.deepgram.com/signup?jump=keys
DEEPGRAM_API_KEY = 'API_KEY'
# Path to a .wav file for transcription
PATH_TO_FILE = 'PATH_TO_WAV_FILE'


# On some windows machines using the deepgram API gives an error with SSL certificates.
# urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1002)>
# This has to do with expiration of ISRG root cert that somehow windows is not able to resolve correctly.
# This issue needs to have a resolutionn
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
