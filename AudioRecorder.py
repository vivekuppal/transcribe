from datetime import datetime
from abc import abstractmethod
# import custom_speech_recognition as sr
import speech_recognition as sr
# import pyaudiowpatch as pyaudio
import pyaudio
import platform
import app_logging as al

# Attempt transcription of the sound file after every RECORD_TIMEOUT seconds
RECORD_TIMEOUT = 1
ENERGY_THRESHOLD = 1000
DYNAMIC_ENERGY_THRESHOLD = False

MBP_SPEAKER_NAME = "MacBook Pro Speakers"
MBP_MIC_NAME = "MacBook Pro Microphone"

PLANTRONICS_3220_MIC_NAME = "Plantronics Blackwire 3220 Series"
HUMAN_MIC_NAME = PLANTRONICS_3220_MIC_NAME
# macOS specific, see README.md#macos for the details on how to configure the BlackHole device
BLACKHOLE_MIC_NAME = "BlackHole 2ch"

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

# This needs to be formatted better
# Attempt to get more info from it like, device_type Mic vs speaker
def print_detailed_audio_info_2():
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f'Audio device with name "{name}" found at index {index}')


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
    def __init__(self, source, source_name):
        root_logger.info(BaseRecorder.__name__)
        self.recorder = sr.Recognizer()
        self.recorder.energy_threshold = ENERGY_THRESHOLD
        self.recorder.dynamic_energy_threshold = DYNAMIC_ENERGY_THRESHOLD
        # Determines if this device is being used for transcription
        self.enabled = True

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source
        self.source_name = source_name

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
        root_logger.info(BaseRecorder.adjust_for_noise.__name__)
        print(f"[INFO] Adjusting for ambient noise from {device_name}. " + msg)
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)
        print(f"[INFO] Completed ambient noise adjustment.")

    def record_into_queue(self, audio_queue):
        def record_callback(_, audio: sr.AudioData) -> None:
            if self.enabled:
                data = audio.get_raw_data()
                audio_queue.put((self.source_name, data, datetime.utcnow()))

        self.recorder.listen_in_background(self.source, record_callback,
                                           phrase_time_limit=RECORD_TIMEOUT)


class MicRecorder(BaseRecorder):
    """Encapsultes the Microphone device audio input
    """
    def __init__(self):
        root_logger.info(MicRecorder.__name__)
        os_name = platform.system()
        self.device_index = None
        default_mic = None

        if os_name == 'Windows':
            py_audio = pyaudio.PyAudio()
            # WASAPI is windows specific
            wasapi_info = py_audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            self.device_index = wasapi_info["defaultInputDevice"]
            default_mic = py_audio.get_device_info_by_index(self.device_index)

            self.device_info = default_mic

            source = sr.Microphone(device_index=default_mic["index"],
                                   sample_rate=int(default_mic["defaultSampleRate"])
                                   # channels=default_mic["maxInputChannels"]
                                   )
            self.source = source
            py_audio.terminate()

        elif os_name == 'Darwin':
            # audio = sr.Microphone.get_pyaudio().PyAudio()
            # Prints a list of all devices
            # for i in range(audio.get_device_count()):
            #    device_info = audio.get_device_info_by_index(i)
            #    print(f'Name: {device_info.get("name")}, InputChannels: {device_info.get("maxInputChannels")} OutputChannels: {device_info.get("maxOutputChannels")}')
            #
            # Prints device info to see all fields inside the device info object
            # print(device_info)
            # audio.terminate()

            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f'Microphone with name "{name}" found for device_index={index})')

                if name == HUMAN_MIC_NAME:
                    self.device_index = index
            
            py_audio = pyaudio.PyAudio()
            if self.device_index is not None:
                default_mic = py_audio.get_device_info_by_index(self.device_index)

            self.device_info = default_mic

            source = sr.Microphone(
                device_index=self.device_index,
                chunk_size=pyaudio.get_sample_size(pyaudio.paInt16)
                )
            py_audio.terminate()

            print(f'[DEBUG] "{MBP_MIC_NAME}" microphone index is: {self.device_index}')

        super().__init__(source=source, source_name="You")
        print(f'[INFO] Listening to sound from Microphone: {self.get_name()} ')
        # This line is commented because in case of non default microphone it can occasionally take
        # several minutes to execute, thus delaying the start of the application.
        self.adjust_for_noise("Default Mic", "Please make some noise from the Default Mic...")

    def get_name(self):
        if self.device_info is not None:
            return f'#{self.device_index} - {self.device_info["name"]}'
        return None

    def set_device(self, index: int):
        """Set active device based on index.
        """
        root_logger.info(MicRecorder.set_device.__name__)
        os_name = platform.system()
        if os_name == 'Windows':
            with pyaudio.PyAudio() as py_audio:
                self.device_index = index
                mic = py_audio.get_device_info_by_index(self.device_index)

            source = sr.Microphone(device_index=mic["index"],
                                   sample_rate=int(mic["defaultSampleRate"]),
                                   channels=mic["maxInputChannels"]
                                   )
        
        elif os_name == 'Darwin':
            p = pyaudio.PyAudio()
            self.device_index = index
            mic = p.get_device_info_by_index(self.device_index)
            p.terminate()
            source = sr.Microphone(device_index=mic["index"],
                                   sample_rate=int(mic["defaultSampleRate"])
                                   )

        self.device_info = mic

        self.source = source
        print(f'[INFO] Listening to sound from Microphone: {self.get_name()} ')
        self.adjust_for_noise("Mic", "Please make some noise from the chosen Mic...")


class SpeakerRecorder(BaseRecorder):
    """Encapsultes the Speaer device audio input
    """
    def __init__(self):
        root_logger.info(SpeakerRecorder.__name__)

        os_name = platform.system()
        self.device_index = None

        if os_name == 'Windows':
            p = pyaudio.PyAudio()
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
            p.terminate()
            source = sr.Microphone(speaker=True,
                                   device_index=default_speakers["index"],
                                   sample_rate=int(default_speakers["defaultSampleRate"]),
                                   chunk_size=pyaudio.get_sample_size(pyaudio.paInt16),
                                   channels=default_speakers["maxInputChannels"])
        elif os_name == 'Darwin':
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                # print("Microphone with name \"{1}\" found for `Microphone(device_index={0})`".format(index, name))
                if name == BLACKHOLE_MIC_NAME:
                    self.device_index = index

            p = pyaudio.PyAudio()
            source = sr.Microphone(
                device_index=self.device_index,
                chunk_size=pyaudio.get_sample_size(pyaudio.paInt16)
                )
            default_speakers = p.get_device_info_by_index(self.device_index)
            p.terminate()

            print("[DEBUG] \"{}\" microphone index is: {}".format(BLACKHOLE_MIC_NAME, self.device_index))

        self.device_info = default_speakers

        super().__init__(source=source, source_name="Speaker")
        print(f'[INFO] Listening to sound from Speaker: {self.get_name()} ')
        self.adjust_for_noise("Default Speaker",
                              "Please play sound from Default Speaker...")

    def get_name(self):
        return f'#{self.device_index} - {self.device_info["name"]}'

    def set_device(self, index: int):
        """Set active device based on index.
        """
        root_logger.info(SpeakerRecorder.set_device.__name__)
        os_name = platform.system()

        if os_name == 'Windows':
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

        elif os_name == 'Darwin':
            p = pyaudio.PyAudio()
            self.device_index = index
            speakers = p.get_device_info_by_index(self.device_index)
            p.terminate()

        self.device_info = speakers

        source = sr.Microphone(speaker=True,
                               device_index=speakers["index"],
                               sample_rate=int(speakers["defaultSampleRate"]),
                               chunk_size=pyaudio.get_sample_size(pyaudio.paInt16),
                               channels=speakers["maxInputChannels"])
        self.source = source
        print(f'[INFO] Listening to sound from Speaker: {self.get_name()} ')
        self.adjust_for_noise("Speaker", 
                              f"Please play sound from selected Speakers {self.get_name()}...")


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
