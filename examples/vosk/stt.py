import json
import vosk
import wave


# Loglevel varies from 1 - 6
# vosk.SetLogLevel(6)
model = vosk.Model(lang="en-us")
filename = '..\\wav\\1.wav'
# filename = '..\\wav\\2.wav'
# filename = '..\\wav\\3.wav'

# Compared to whisper STT, vosk lacks punctuation and is slightly
# slower for most samples that were tried.

wf = wave.open(filename, 'rb')
rec = vosk.KaldiRecognizer(model, wf.getframerate())

# Use this to determine the start, end times of each word
# rec.SetWords(True)
# rec.SetPartialWords(True)

while True:
    data = wf.readframes(200000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        data = json.loads(rec.Result())
        size = len(data)
        # print(f'type: {type(data)} len: {size} data: <{data["text"]}>')
        if size == 1 and data['text'] == "":
            continue
        print(f'{data}')

print(f'{rec.FinalResult()}')
