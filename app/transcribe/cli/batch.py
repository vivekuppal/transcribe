"""Batch and headless CLI task execution."""

from __future__ import annotations

import os
import re

import openai
import yaml
from sdk import audio_recorder as ar

from .. import interactions
from ..providers.stt import convert_audio_to_16khz, create_stt_model

from tsutils import configuration, duration, utilities


def handle_batch_tasks(args, config: dict) -> bool:
    """Handle headless CLI tasks. Returns True when a task was executed."""
    interactions.params(args)

    if args.list_devices:
        print("\n\nList all audio drivers and devices on this machine")
        ar.print_detailed_audio_info()
        return True

    if args.save_api_key is not None:
        save_api_key(args.save_api_key)
        return True

    if args.validate_api_key is not None:
        validate_api_key(api_key=args.validate_api_key, config=config)
        return True

    if args.transcribe is not None:
        transcribe_audio_file(args=args, config=config)
        return True

    return False


def validate_api_key(api_key: str, config: dict):
    """Validate an OpenAI-compatible API key."""
    chat_inference_provider = config["General"]["chat_inference_provider"]
    settings_section = "OpenAI" if chat_inference_provider == "openai" else "Together"

    base_url = config[settings_section]["base_url"]
    model = config[settings_section]["ai_model"]

    if utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
        print("The api_key is valid")
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        if base_url != "https://api.together.xyz":
            models = utilities.get_available_models(client=client)
            print("Available models: ")
            for available_model in models:
                print(f"    {available_model}")
        client.close()
    else:
        print("The api_key is not valid")


def transcribe_audio_file(args, config: dict):
    """Run file transcription without starting the desktop runtime."""
    output_file = args.output_file if args.output_file is not None else "transcription.txt"
    safe_filename = re.sub("[^0-9a-zA-Z\\.]+", "_", output_file)
    stt_name = config["General"]["stt"]
    use_api = bool(config["General"]["use_api"])

    with duration.Duration(name="Transcription", log=False, screen=True):
        print(f"Converting the audio file {args.transcribe} to text.")
        print(f"{args.transcribe} file size {utilities.naturalsize(os.path.getsize(args.transcribe))}.")
        print(f"Text output will be produced in {safe_filename}.")

        file_path = args.transcribe
        temp_file_path = None
        try:
            if stt_name == "whisper.cpp":
                temp_file_path = convert_audio_to_16khz(args.transcribe)
                file_path = temp_file_path

            model = create_stt_model(name=stt_name, config=config, api=use_api)
            results = model.get_sentences(file_path)
        finally:
            if temp_file_path is not None and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        if results is not None and len(results) > 0:
            with open(safe_filename, encoding="utf-8", mode="w") as file_handle:
                for sentence in results:
                    file_handle.write(f"{sentence.strip()}\n")
            print("Complete!")
            return

        print("Error during Transcription!")
        print(f"Please ensure {args.transcribe} is an audio file.")
        raise SystemExit(1)


def save_api_key(api_key: str):
    """Persist the API key to the override configuration."""
    yml = configuration.Config()
    with open(yml.config_override_file, mode="r", encoding="utf-8") as file:
        altered_config = yaml.load(stream=file, Loader=yaml.SafeLoader)

    if altered_config is None:
        altered_config = {}
    if "OpenAI" not in altered_config:
        altered_config["OpenAI"] = {}
    altered_config["OpenAI"]["api_key"] = api_key
    yml.add_override_value(altered_config)
    print(f"Saved API Key to {yml.config_override_file}")
