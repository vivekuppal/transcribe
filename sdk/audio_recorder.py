import sys
from datetime import datetime
import time
from abc import abstractmethod
import queue
import wave
import os
import pyaudiowpatch as pyaudio
import custom_speech_recognition as sr
from tsutils import app_logging as al
sys.path.append('../..')
from tsutils import configuration  # noqa: E402 pylint: disable=C0413

ENERGY_THRESHOLD = 1000
DYNAMIC_ENERGY_THRESHOLD = False

root_logger = al.get_logger()


# https://people.csail.mit.edu/hubert/pyaudio/docs/#id6
driver_type = {
    -1: 'Not actually an audio device',
    0: 'Still in development',
    1: 'DirectSound (Windows only)',
    2: 'Multimedia Extension (Windows only)',
    3: 'Steinberg Audio Stream Input/Output',
    4: 'SoundManager (OSX only)',
    5: 'CoreAudio (OSX only)',
    7: 'Open Sound System (Linux only)',
    8: 'Advanced Linux Sound Architecture (Linux only)',
    9: 'Open Audio Library',
    10: 'BeOS Sound System',
    11: 'Windows Driver Model (Windows only)',
    12: 'JACK Audio Connection Kit',
    13: 'Windows Vista Audio stack architecture'
}


def print_detailed_audio_info(print_func=print):
    """
    Print information about Host APIs and devices,
    using `print_func`.

    :param print_func: Print function(or wrapper)
    :type print_func: function
    :rtype: None
    """
    print_func("\n|", "~ Audio Drivers on this machine ~".center(20), "|\n")
    header = f" ^ #{'INDEX'.center(7)}#{'DRIVER TYPE'.center(13)}#{'DEVICE COUNT'.center(15)}#{'NAME'.center(5)}"
    print_func(header)
    print_func("-"*len(header))
    py_audio = pyaudio.PyAudio()
    for host_api in py_audio.get_host_api_info_generator():
        print_func(
            (
                f" » "
                f"{('['+str(host_api['index'])+']').center(8)}|"
                f"{str(host_api['type']).center(13)}|"
                f"{str(host_api['deviceCount']).center(15)}|"
                f"  {host_api['name']}"
            )
        )

    print_func("\n\n\n|", "~ Audio Devices on this machine ~".center(20), "|\n")
    header = f" ^ #{'INDEX'.center(7)}# HOST API INDEX #{'LOOPBACK'.center(10)}#{'NAME'.center(5)}"
    print_func(header)
    print_func("-"*len(header))
    for device in py_audio.get_device_info_generator():
        print_func(
            (
                f" » "
                f"{('['+str(device['index'])+']').center(8)}"
                f"{str(device['hostApi']).center(16)}"
                f"  {str(device['isLoopbackDevice']).center(10)}"
                f"  {device['name']}"
            )
        )

    # Below statements are useful to view all available fields in the
    # driver and device list
    # Do not remove these statements from here
    # print('Windows Audio Drivers')
    # for host_api_info_gen in py_audio.get_host_api_info_generator():
    #    print(host_api_info_gen)

    # print('Windows Audio Devices')
    # for device_info_gen in py_audio.get_device_info_generator():
    #    print(device_info_gen)


class BaseRecorder:
    """Base class for Speaker, Microphone classes
    """
    def __init__(self, source, source_name, audio_file_name: str = None):
        root_logger.info(BaseRecorder.__name__)
        self.recorder = sr.Recognizer()
        self.recorder.energy_threshold = ENERGY_THRESHOLD
        self.recorder.dynamic_energy_threshold = DYNAMIC_ENERGY_THRESHOLD
        # Determines if this device is being used for transcription
        self.enabled: bool = True

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source
        self.source_name: str = source_name
        self.config = configuration.Config().data
        self.stop_record_func = None
        self.audio_file_name = audio_file_name
        if self.audio_file_name and os.path.exists(self.audio_file_name):
            os.remove(self.audio_file_name)
        if self.audio_file_name and os.path.exists(self.audio_file_name+'.bak'):
            os.remove(self.audio_file_name+'.bak')

    @abstractmethod
    def get_name(self):
        """Get the name of this device
        """

    def enable(self):
        """Enable transcription from this device
        """
        self.enabled = True

    def disable(self):
        """Disable transcription from this device
        """
        self.enabled = False

    def adjust_for_noise(self, device_name, msg):
        """Adjust based on noise from surroundings.
        """
        root_logger.info(BaseRecorder.adjust_for_noise.__name__)
        print(f"[INFO] Adjusting for ambient noise from {device_name}. " + msg)
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)
        print(f"[INFO] Completed ambient noise adjustment for {device_name}.")

    def record_audio(self, audio_queue: queue.Queue):
        """Start recording audion from the stream and add data to queue
        """
        def record_callback(_, audio: sr.AudioData) -> None:
            if self.enabled:
                data = audio.get_raw_data()
                audio_queue.put((self.source_name, data, datetime.utcnow()))
                if self.audio_file_name:
                    with open(file=self.audio_file_name+'.bak', mode='ab') as file_handle:
                        file_handle.write(data)

        stop_func = self.recorder.listen_in_background(source=self.source,
                                                       source_name=self.source_name,
                                                       callback=record_callback,
                                                       phrase_time_limit=self.config['General']['transcript_audio_duration_seconds'])
        return stop_func

    def write_wav_data_to_file(self) -> str:
        """Write the raw input data into a wave file
        """
        if self.audio_file_name is None:
            return

        if not os.path.exists(self.audio_file_name+'.bak'):
            return

        frame_rate = self.source.SAMPLE_RATE
        sample_width = self.source.SAMPLE_WIDTH
        channels = self.source.channels

        with open(file=self.audio_file_name+'.bak', mode='rb') as input_file_handle:
            data = input_file_handle.read()

        with wave.open(self.audio_file_name, 'wb') as wf:
            # print(f'{datetime.datetime.now()} - Writing speaker data into file: {file_path}')
            wf.setnchannels(channels)    # pylint: disable=E1101
            wf.setsampwidth(sample_width)    # pylint: disable=E1101
            wf.setframerate(frame_rate)    # pylint: disable=E1101
            wf.writeframes(data)    # pylint: disable=E1101
            print(f'datasize: {len(data)}')
        print(f'filesize: {os.path.getsize(self.audio_file_name)}')


class MicRecorder(BaseRecorder):
    """Encapsultes the Microphone device audio input
    """
    def __init__(self, source_name='You', audio_file_name: str = None):
        self.source = sr.Microphone(sample_rate=16000)
        self.device_index = self.source.device_index
        self.device_info = None
        super().__init__(source=self.source, source_name=source_name, audio_file_name=audio_file_name)
        self.adjust_for_noise("Default Mic", "Please make some noise from the Default Mic...")

#    def __init__(self):
#        root_logger.info(MicRecorder.__name__)
#        with pyaudio.PyAudio() as py_audio:
#             WASAPI is windows specific
#            wasapi_info = py_audio.get_host_api_info_by_type(pyaudio.paWASAPI)
#            self.device_index = wasapi_info["defaultInputDevice"]
#            default_mic = py_audio.get_device_info_by_index(self.device_index)

#        self.device_info = default_mic
#        print(f'default_mic: {default_mic}')

#        source = sr.Microphone(device_index=default_mic["index"],
#                               sample_rate=int(default_mic["defaultSampleRate"]),
#                               channels=1
#                               )
#        self.source = source
#        super().__init__(source=source, source_name="You")
#        print(f'[INFO] Listening to sound from Microphone: {self.get_name()} ')
        # This line is commented because in case of non default microphone it can occasionally take
        # several minutes to execute, thus delaying the start of the application.
#        self.adjust_for_noise("Default Mic", "Please make some noise from the Default Mic...")

    def get_name(self):
        return f'#{self.device_index} - {self.device_info["name"]}'

    def set_device(self, index: int):
        """Set active device based on index.
        """
        root_logger.info(MicRecorder.set_device.__name__)
        with pyaudio.PyAudio() as py_audio:
            self.device_index = index
            mic = py_audio.get_device_info_by_index(self.device_index)

        # Stop the current stream
        if self.stop_record_func is not None:
            self.stop_record_func(wait_for_stop=False)
            time.sleep(2)
        self.device_info = mic
        self.source = sr.Microphone(device_index=mic["index"],
                                    sample_rate=int(mic["defaultSampleRate"]),
                                    channels=1
                                    )

        print(f'[INFO] Listening to sound from Microphone: {self.get_name()} ')
        self.adjust_for_noise("Mic", "Please make some noise from the chosen Mic...")


class SpeakerRecorder(BaseRecorder):
    """Encapsultes the Speaer device audio input
    """
    def __init__(self, source_name='Speaker', audio_file_name: str = None):
        root_logger.info(SpeakerRecorder.__name__)
        with pyaudio.PyAudio() as p:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            self.device_index = wasapi_info["defaultOutputDevice"]
            default_speakers = p.get_device_info_by_index(self.device_index)

            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break
                else:
                    print("[ERROR] No loopback device found.")

        self.device_info = default_speakers

        source = sr.Microphone(speaker=True,
                               device_index=default_speakers["index"],
                               sample_rate=int(default_speakers["defaultSampleRate"]),
                               chunk_size=pyaudio.get_sample_size(pyaudio.paInt16),
                               channels=default_speakers["maxInputChannels"])
        super().__init__(source=source, source_name=source_name, audio_file_name=audio_file_name)
        print(f'[INFO] Listening to sound from Speaker: {self.get_name()} ')
        # On some devices, speaker adjustment is very slow unless some noise is
        # made from the speakers, though capturing of speaker output is very
        # good in almost all instances I have seen thus far.
        # self.adjust_for_noise("Default Speaker",
        #                       "Please play sound from Default Speaker...")

    def get_name(self):
        return f'#{self.device_index} - {self.device_info["name"]}'

    def set_device(self, index: int):
        """Set active device based on index.
        """
        root_logger.info(SpeakerRecorder.set_device.__name__)
        with pyaudio.PyAudio() as p:
            self.device_index = index
            speakers = p.get_device_info_by_index(self.device_index)

            if not speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if speakers["name"] in loopback["name"]:
                        speakers = loopback
                        break
                else:
                    print("[ERROR] No loopback device found.")

        # Stop the current stream
        if self.stop_record_func is not None:
            self.stop_record_func(wait_for_stop=False)
            time.sleep(2)

        self.device_info = speakers
        self.source = sr.Microphone(speaker=True,
                                    device_index=speakers["index"],
                                    sample_rate=int(speakers["defaultSampleRate"]),
                                    chunk_size=pyaudio.get_sample_size(pyaudio.paInt16),
                                    channels=speakers["maxInputChannels"])

        print(f'[INFO] Listening to sound from Speaker: {self.get_name()}')
        # self.adjust_for_noise("Speaker",
        #                       f"Please play sound from selected Speakers {self.get_name()}...")


if __name__ == "__main__":
    print_detailed_audio_info()
    # Below statements are useful to view all available fields in the
    # default Input Device.
    # Do not delete these lines
    # with pyaudio.PyAudio() as p:
    #     wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    #     print(wasapi_info)

    # with pyaudio.PyAudio() as p:
    #    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    #    default_mic = p.get_device_info_by_index(wasapi_info["defaultInputDevice"])
    #    print(default_mic)
