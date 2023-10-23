# Batch Operations #

## Transcribe any audio file
Any audio file can be transcribed using the `-t` option

```
  -t TRANSCRIBE, --transcribe TRANSCRIBE
                        Transcribe the given audio file to generate text.
                        This option respects the -m (model) option.
                        Output is produced in transcription.txt or file specified using the -o option.

E.g.

python main.py -t C:\j\sample_audio.wav -o transcription.txt

```

## Transcribe any video

Transcribe text of any video by playing the video and running transcribe at the same time. Once the video finishes, ensure the text in transcription window is not updating anymore. Save the text to file using the menu option

`File -> Save transcript to File`
