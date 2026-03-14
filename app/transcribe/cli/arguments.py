"""CLI argument definitions and config overrides."""

import argparse
from argparse import RawTextHelpFormatter


def create_args() -> argparse.Namespace:
    """Set up command line arguments for the application."""
    cmd_args = argparse.ArgumentParser(
        description="Command Line Arguments for Transcribe",
        formatter_class=RawTextHelpFormatter,
    )
    cmd_args.add_argument(
        "-a",
        "--api",
        action="store_true",
        help="Use the online Open AI API for transcription.\nThis option requires an API KEY and will consume Open AI credits.",
    )
    cmd_args.add_argument(
        "-e",
        "--experimental",
        action="store_true",
        help="Experimental command line argument. Behavior is undefined.",
    )
    cmd_args.add_argument(
        "-stt",
        "--speech_to_text",
        action="store",
        default=None,
        choices=["whisper", "whisper.cpp", "deepgram"],
        help="Specify the Speech to text Engine.\nLocal STT models tend to perform best for response times.\nAPI based STT models tend to perform best for accuracy.",
    )
    cmd_args.add_argument(
        "-c",
        "--chat-inference-provider",
        action="store",
        default="openai",
        choices=["openai", "together"],
        help="Specify the Chat Inference engine.",
    )
    cmd_args.add_argument(
        "-k",
        "--api_key",
        action="store",
        default=None,
        help="API Key for accessing OpenAI APIs. This is an optional parameter.\nWithout the API Key only transcription works.\nThis option will not save the API key anywhere, to persist the API key use the -sk option.",
    )
    cmd_args.add_argument(
        "-sk",
        "--save_api_key",
        action="store",
        default=None,
        help="Save the API key for accessing OpenAI APIs to override.yaml file.\nSubsequent invocations of the program will not require API key on command line.\nTo not persist the API key use the -k option.",
    )
    cmd_args.add_argument(
        "-vk",
        "--validate_api_key",
        action="store",
        default=None,
        help="Validate that it is a valid functioning api_key.\nWithout the API Key only transcription works.",
    )
    cmd_args.add_argument(
        "-t",
        "--transcribe",
        action="store",
        default=None,
        help="Transcribe the given audio file to generate text.\nThis option respects the -m (model) option.\nOutput is produced in transcription.txt or file specified using the -o option.",
    )
    cmd_args.add_argument(
        "-o",
        "--output_file",
        action="store",
        default=None,
        help="Generate output in this file.\nThis option is valid only for the -t (transcribe) option.",
    )
    cmd_args.add_argument(
        "-m",
        "--model",
        action="store",
        choices=["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"],
        default="base",
        help="Specify the OpenAI Local Transcription model file to use.\nThe necessary model files will be downloaded once at run time.",
    )
    cmd_args.add_argument(
        "-l",
        "--list_devices",
        action="store_true",
        help="List all audio drivers and audio devices on this machine.\nUse this list index to select the microphone, speaker device for transcription.",
    )
    cmd_args.add_argument(
        "-mi",
        "--mic_device_index",
        action="store",
        default=None,
        type=int,
        help="Device index of the microphone for capturing sound.\nDevice index can be obtained using the -l option.",
    )
    cmd_args.add_argument(
        "-si",
        "--speaker_device_index",
        action="store",
        default=None,
        type=int,
        help="Device index of the speaker for capturing sound.\nDevice index can be obtained using the -l option.",
    )
    cmd_args.add_argument("-dm", "--disable_mic", action="store_true", help="Disable transcription from Microphone")
    cmd_args.add_argument("-ds", "--disable_speaker", action="store_true", help="Disable transcription from Speaker")
    return cmd_args.parse_args()


def update_args_config(args: argparse.Namespace, config: dict):
    """Apply CLI overrides onto the in-memory configuration."""
    if args.api_key is not None:
        config["OpenAI"]["api_key"] = args.api_key

    if args.model is not None:
        config["OpenAI"]["local_transcripton_model_file"] = args.model
        config["WhisperCpp"]["local_transcripton_model_file"] = args.model
    else:
        config["OpenAI"]["local_transcripton_model_file"] = "base"
        config["WhisperCpp"]["local_transcripton_model_file"] = "base"

    if args.api:
        config["General"]["use_api"] = args.api

    if args.disable_mic:
        config["General"]["disable_mic"] = args.disable_mic

    if args.mic_device_index is not None:
        config["General"]["mic_device_index"] = int(args.mic_device_index)

    if args.disable_speaker:
        config["General"]["disable_speaker"] = args.disable_speaker

    if args.speaker_device_index is not None:
        config["General"]["speaker_device_index"] = int(args.speaker_device_index)

    if args.speech_to_text is not None:
        config["General"]["stt"] = args.speech_to_text
