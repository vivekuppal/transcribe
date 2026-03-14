"""LLM provider composition for the application."""

from ..gpt_responder import InferenceResponderFactory, InferenceEnum


def create_responder(provider_name: str, config, convo, save_to_file: bool, response_file_name: str):
    """Create a responder / inference provider object based on the selected provider."""
    responder_factory = InferenceResponderFactory()

    if provider_name.lower() == "openai":
        return responder_factory.get_responder_instance(
            provider=InferenceEnum.OPENAI,
            config=config,
            convo=convo,
            save_to_file=save_to_file,
            response_file_name=response_file_name,
        )

    if provider_name.lower() == "together":
        return responder_factory.get_responder_instance(
            provider=InferenceEnum.TOGETHER,
            config=config,
            convo=convo,
            save_to_file=save_to_file,
            response_file_name=response_file_name,
        )

    return None
