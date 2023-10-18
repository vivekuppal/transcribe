import os
import whisper
import wave
import struct
import io

# Sample python file to manipulate the WAVfile.
# Currently this file / class is not used in the transcribe at run time

class WAVFile:

    def __init__(self, filename):
        self.filename = filename

    def read(self):
        with io.open(self.filename, 'rb') as fh:
            riff, size, fformat = struct.unpack('<4sI4s', fh.read(12))
            print("Riff: %s, Chunk Size: %i, format: %s" % (riff, size, fformat))

            # Read header
            chunk_header = fh.read(8)
            subchunkid, subchunksize = struct.unpack('<4sI', chunk_header)

            if subchunkid == b'fmt ':
                aformat, channels, samplerate, byterate, blockalign, bps = struct.unpack('HHIIHH', fh.read(16))
                bitrate = (samplerate * channels * bps) / 1024
                print(f'Format: {aformat}, Channels {channels}, '
                      f'Sample Rate: {samplerate}, Kbps: {bitrate}')

            chunkOffset = fh.tell()
            while chunkOffset < size:
                fh.seek(chunkOffset)
                subchunk2id, subchunk2size = struct.unpack('<4sI', fh.read(8))
                print(f'chunk id: {subchunk2id}, size: {subchunk2size}')
                if subchunk2id == b'LIST':
                    listtype = struct.unpack('<4s', fh.read(4))
                    print('\tList Type: {listtype}, List Size: {subchunk2size}')

                    listOffset = 0
                    while (subchunk2size - 8) >= listOffset:
                        listitemid, listitemsize = struct.unpack('<4sI', fh.read(8))
                        listOffset = listOffset + listitemsize + 8
                        listdata = fh.read(listitemsize)
                        print(f"\tList id {listitemid.decode('ascii')}, size: {listitemsize},"
                              f" data: {listdata.decode('ascii')}")
                        print("\tOffset: {listOffset}")
                elif subchunk2id == b'data':
                    print("Found data")
                else:
                    print(f"Data: {fh.read(subchunk2size).decode('ascii')}")

                chunkOffset = chunkOffset + subchunk2size + 8


# input_file = 'C:\\Users\\vivek\\AppData\\Local\\Temp\\tmpesnnlmk_.wav'
# input_file = 'C:\\Users\\vivek\\AppData\\Local\\Temp\\tmppablqctf.wav'
# input_file = 'C:\\Users\\vivek\\AppData\\Local\\Temp\\tmp5hjs1as3.wav'


# input_file = 'C:\\j\\test\\1.wav'
# Evaluating file C:\j\test\1.wav
# It is a valid input file.
# Riff: b'RIFF', Chunk Size: 2944660, format: b'WAVE'
# Format: 1, Channels 2, Sample Rate: 48000, Kbps: 1500.0
# chunk id: b'data', size: 2944624
# Found data
# ball that have been hit over 500 In the winter. Take a good look you won't see
# b'\x10\x00\x03\x00'
# b'\x14\x00\x01\x00\x18\x00\xfd\xff'

input_file = 'C:\\j\\test\\2.wav'
# Evaluating file C:\j\test\2.wav
# It is a valid input file.
# Riff: b'RIFF', Chunk Size: 3520660, format: b'WAVE'
# Format: 1, Channels 2, Sample Rate: 48000, Kbps: 1500.0
# chunk id: b'data', size: 3520624
# Found data
# ball that have been hit over 500 feet. In the winter. Oh boy. That's good. Take a good look you won't see this one for long. CJ.
# b'\x10\x00\x03\x00'
# b'\x14\x00\x01\x00\x18\x00\xfd\xff'

# input_file = 'C:\\j\\test\\3.wav'
# Evaluating file C:\j\test\3.wav
# It is a valid input file.
# Riff: b'RIFF', Chunk Size: 3412095, format: b'WAVE'
# Format: 1, Channels 2, Sample Rate: 48000, Kbps: 1500.0
# chunk id: b'data', size: 3412059
# Found data
# G角 a
# b'\xff#\xff='
# b'\xff=\xffX\xffY\xffp'

# Read file 2.
# Trim to a lower size.
# Save to another file.
# Transcribe successfully

output_file = 'C:\\j\\test\\output.wav'

try:
    print(f'Evaluating file {input_file}')
    print(f'filesize: {os.path.getsize(input_file)}')
    with wave.open(input_file, 'rb') as f:
        print('It is a valid input file.')
except wave.Error:
    print('It is an invalid input file.')

wavFile = WAVFile(input_file)
wavFile.read()

model = whisper.load_model("base")
result = model.transcribe(input_file)
len_segments = len(result["segments"])
for segment in result["segments"]:
    print(f'id: {segment["id"]} start: {segment["start"]} end: {segment["end"]} ' +
          f'text: {segment["text"].strip()}')
prune_segment_id = 2
print(f'Prune the first {prune_segment_id} segments.')

prune_segment = result["segments"][prune_segment_id]
original_duration = result["segments"][len_segments-1]["end"]
prune_seconds = prune_segment['end']
prune_percent = prune_seconds / original_duration
print(f'Prune till segment id : {prune_segment_id}. Prune duration: {prune_seconds}.')
print(f'Prune {prune_percent}% of data.')

print(result["text"])

with wave.open(input_file, 'rb') as wf:
    # Read the header
    num_frames = wf.getnframes()
    print(f'{input_file} has {num_frames} frames.')
    save_frames = int(num_frames * prune_percent)
    with wave.open(output_file, 'wb') as new_wavfile:
        new_wavfile.setnchannels(wf.getnchannels())
        new_wavfile.setsampwidth(wf.getsampwidth())
        new_wavfile.setframerate(wf.getframerate())
        wf.setpos(save_frames)
        new_wavfile.writeframes(wf.readframes(num_frames - int(save_frames)))

result = model.transcribe(output_file)
print('Shortened audio file transcription.')
print(result["text"])
# Get the number of frames
#    for i in range(0, num_frames, 1024):
#        new_wavfile.setnchannels(wavfile.getnchannels())
#        new_wavfile.setsampwidth(wavfile.getsampwidth())
#        new_wavfile.setframerate(wavfile.getframerate())
#        new_wavfile.writeframes(wavfile.readframes(1024))
