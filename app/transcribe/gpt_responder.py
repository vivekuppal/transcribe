import datetime
import time
from enum import Enum
# import pprint
import openai
import prompts
import conversation
import constants
from db import (
    AppDB as appdb,
    llm_responses as llmrdb,
    summaries as s)
from tsutils import app_logging as al
from tsutils import duration, utilities


root_logger = al.get_logger()


class InferenceEnum(Enum):
    """Supported Chat Inference Providers
    """
    OPENAI = 1
    TOGETHER = 2


class GPTResponder:
    """Handles all interactions with openAI LLM / ChatGPT
    """
    # By default we do not ping LLM to get data
    enabled: bool = False
    model: str = None
    llm_client = None

    def __init__(self,
                 config: dict,
                 convo: conversation.Conversation,
                 save_to_file: bool = False,
                 file_name: str = 'logs/response.txt',
                 openai_module=openai):
        root_logger.info(GPTResponder.__name__)
        # This var is used by UI to populate the response textbox
        self.response = prompts.INITIAL_RESPONSE
        self.llm_response_interval = 2
        self.conversation = convo
        self.config = config
        self.save_response_to_file = save_to_file
        self.response_file = file_name
        self.openai_module = openai_module

    def summarize(self) -> str:
        """Ping LLM to get a summary of the conversation.
        """
        root_logger.info(GPTResponder.summarize.__name__)

        chat_inference_provider = self.config['General']['chat_inference_provider']
        if chat_inference_provider == 'openai':
            settings_section = 'OpenAI'
        elif chat_inference_provider == 'together':
            settings_section = 'Together'

        api_key = self.config[settings_section]['api_key']
        base_url = self.config[settings_section]['base_url']
        model = self.config[settings_section]['ai_model']

        if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
            return None

        with duration.Duration(name='OpenAI Summarize', screen=False):
            timeout: int = self.config['OpenAI']['summarize_request_timeout_seconds']
            temperature: float = self.config['OpenAI']['temperature']
            prompt_content = self.conversation.get_merged_conversation_summary()
            prompt_api_message = prompts.create_multiturn_prompt(prompt_content)
            last_convo_id = int(prompt_content[-1][2])
            # self._pretty_print_openai_request(prompt_api_message)
            summary_response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=prompt_api_message,
                    temperature=temperature,
                    timeout=timeout,
                    stream=True
                )
            collected_messages = ""
            for chunk in summary_response:
                chunk_message = chunk.choices[0].delta  # extract the message
                if chunk_message.content:
                    message_text = chunk_message.content
                    collected_messages += message_text
                    # print(f'{message_text}', end="")

            # insert in DB
            inv_id = appdb().get_invocation_id()
            summary_obj = appdb().get_object(s.TABLE_NAME)
            summary_obj.insert_summary(inv_id, last_convo_id, collected_messages)

        return collected_messages

    def _get_settings_section(self, provider: str) -> str:
        """Get the settings section based on the chat inference provider."""
        if provider == 'openai':
            return 'OpenAI'
        elif provider == 'together':
            return 'Together'
        raise ValueError(f"Unsupported chat inference provider: {provider}")

    def _get_api_settings(self, settings_section: str):
        """Retrieve API settings from the configuration."""
        api_key = self.config[settings_section]['api_key']
        base_url = self.config[settings_section]['base_url']
        model = self.config[settings_section]['ai_model']
        return api_key, base_url, model

    def _get_openai_settings(self) -> (int, float):
        """Retrieve OpenAI-specific settings from the configuration."""
        timeout = self.config['OpenAI']['response_request_timeout_seconds']
        temperature = self.config['OpenAI']['temperature']
        return timeout, temperature

    def _get_llm_response(self, messages, temperature, timeout) -> str:
        """Send a request to the LLM and process the streaming response."""
        with duration.Duration(name='OpenAI Chat Completion', screen=False):
            multi_turn_response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                timeout=timeout,
                stream=True
            )

            collected_messages = ""
            for chunk in multi_turn_response:
                chunk_message = chunk.choices[0].delta  # extract the message
                if chunk_message.content:
                    message_text = chunk_message.content
                    collected_messages += message_text
                    self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                              response=collected_messages,
                                              update_previous=True)
            return collected_messages

    def _insert_response_in_db(self, last_convo_id: int, response: str):
        """Insert the generated response into the database."""
        inv_id = appdb().get_invocation_id()
        llmr_obj: llmrdb.LLMResponses = appdb().get_object(llmrdb.TABLE_NAME)
        llmr_obj.insert_response(inv_id, last_convo_id, response)

    def generate_response_from_transcript_no_check(self) -> str:
        """
        Pings the LLM to get a suggested response immediately.

        This method gets a response even if the continuous suggestion option is disabled.
        It updates the conversation object with the response from the LLM.

        Returns:
            str: The generated response from the LLM.
        """
        root_logger.info(GPTResponder.generate_response_from_transcript_no_check.__name__)

        try:
            chat_inference_provider = self.config['General']['chat_inference_provider']
            settings_section = self._get_settings_section(chat_inference_provider)
            api_key, base_url, model = self._get_api_settings(settings_section)

            if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
                return None

            timeout, temperature = self._get_openai_settings()
            multiturn_prompt_content = self.conversation.get_merged_conversation_response(
                length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
            last_convo_id = int(multiturn_prompt_content[-1][2])
            multiturn_prompt_api_message = prompts.create_multiturn_prompt(multiturn_prompt_content)

            collected_messages = self._get_llm_response(multiturn_prompt_api_message, temperature, timeout)
            self._insert_response_in_db(last_convo_id, collected_messages)

            return collected_messages
        except Exception as e:
            root_logger.error(f"Error in generate_response_from_transcript_no_check: {e}")
            return None

    def create_client(self, api_key: str, base_url: str = None):
        """
        Create and initialize an OpenAI API compatible client.

        Args:
            api_key (str): The API key for authentication.
            base_url (str, optional): The base URL for the API. Defaults to None.

        Returns:
            None

        Raises:
            ValueError: If the API key is invalid.
            ConnectionError: If the client fails to connect.
        """
        if not api_key:
            raise ValueError("API key is required")

        try:
            if self.llm_client is not None:
                self.llm_client.close()
            self.llm_client = self.openai_module.OpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            raise ConnectionError(f"Failed to create OpenAI client: {e}")

    def process_response(self, input_str: str) -> str:
        """
        Processes a given input string by extracting relevant data from LLM response.

        Args:
            input_str (str): The input string containing LLM response data.

        Returns:
            str: A processed string with irrelevant content removed.
        """
        if input_str is None:
            raise ValueError("input_str cannot be None")

        lines = input_str.split(sep='\n')
        response_lines = []

        for line in lines:
            # Skip any responses that contain content like
            # Speaker 1: <Some statement>
            # This is generated content added by OpenAI that can be skipped
            if 'Speaker' in line and ':' in line:
                continue
            response_lines.append(line.strip().strip('[').strip(']'))

        # Create a list and then use that to create a string for
        # performance reasons, since strings are immutable in python
        response = ''.join(response_lines)
        return response

    def generate_response_from_transcript(self) -> str:
        """
        Pings the OpenAI LLM model to get a response from the Assistant.

        Logs the method call and checks if the feature is enabled before
        proceeding with response generation.

        Returns:
            str: The response from the OpenAI LLM model.
            Returns an empty string if the feature is disabled.
        """
        root_logger.info("generate_response_from_transcript called")

        if not self.enabled:
            return ''

        return self.generate_response_from_transcript_no_check()

    def generate_response_for_selected_text(self, text: str):
        """Ping LLM to get a suggested response right away.
            Gets a response even if the continuous suggestion option is disabled.
            Updates the conversation object with the response from LLM.
        """
        try:
            root_logger.info(GPTResponder.generate_response_for_selected_text.__name__)
            chat_inference_provider = self.config['General']['chat_inference_provider']

            chat_inference_provider = self.config['General']['chat_inference_provider']
            settings_section = self._get_settings_section(chat_inference_provider)
            api_key, base_url, model = self._get_api_settings(settings_section)

            timeout, temperature = self._get_openai_settings()

            if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
                return None

            with duration.Duration(name='OpenAI Chat Completion Selected', screen=False):
                prompt = prompts.create_prompt_for_text(text=text, config=self.config)
                llm_response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=prompt,
                    temperature=temperature,
                    timeout=timeout,
                    stream=True
                )

                # Update conversation with an empty response. This response will be updated
                # by subsequent updates from the streaming response
                self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                          response="  ",
                                          update_previous=False)
                collected_messages = ""
                for chunk in llm_response:
                    chunk_message = chunk.choices[0].delta  # extract the message
                    if chunk_message.content:
                        message_text = chunk_message.content
                        collected_messages += message_text
                        # print(f"{message_text}", end="")
                        self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                                  response=collected_messages,
                                                  update_previous=True)

        except Exception as exception:
            print('Error when attempting to get a response from LLM.')
            print(exception)
            root_logger.error('Error when attempting to get a response from LLM.')
            root_logger.exception(exception)
            return prompts.INITIAL_RESPONSE

        processed_response = collected_messages

        if self.save_response_to_file:
            with open(file=self.response_file, mode="a", encoding='utf-8') as f:
                f.write(f'{datetime.datetime.now()} - {processed_response}\n')

        return processed_response

    def _update_conversation(self, response, persona, update_previous=False):
        """Update the internaal conversation state"""
        root_logger.info(GPTResponder._update_conversation.__name__)
        if response != '':
            self.response = response
            self.conversation.update_conversation(persona=persona,
                                                  text=response,
                                                  time_spoken=datetime.datetime.utcnow(),
                                                  update_previous=update_previous)

    def respond_to_transcriber(self, transcriber):
        """Thread method to continously update the transcript
        """
        while True:

            # Attempt to get responses only if transcript has changed
            if transcriber.transcript_changed_event.is_set():
                start_time = time.time()

                transcriber.transcript_changed_event.clear()

                # Do processing only if LLM transcription is enabled
                if self.enabled:
                    self.generate_response_from_transcript()

                end_time = time.time()  # Measure end time
                execution_time = end_time - start_time  # Calculate time to execute the function

                remaining_time = self.llm_response_interval - execution_time
                if remaining_time > 0:
                    time.sleep(remaining_time)
            else:
                time.sleep(self.llm_response_interval)

    def update_response_interval(self, interval):
        """Change the interval for pinging LLM
        """
        root_logger.info(GPTResponder.update_response_interval.__name__)
        self.llm_response_interval = interval

    def _pretty_print_openai_request(self, message: str):
        """Format the openAI request in a nice print format"""
        print('[')
        for item in message:
            print('  {')
            print(f'    \'role\': \'{item["role"]}\'')
            print(f'    \'content\': \'{item["content"]}\'')
            print('  }')

        print(']')


class OpenAIResponder(GPTResponder):
    """Uses OpenAI for Chat Inference"""

    def __init__(self,
                 config: dict,
                 convo: conversation.Conversation,
                 save_to_file: bool = False,
                 base_url: str = None,
                 response_file_name: str = 'logs/response.txt'):
        root_logger.info(OpenAIResponder.__name__)
        self.config = config
        api_key = self.config['OpenAI']['api_key']
        base_url = self.config['OpenAI']['base_url']
        self.llm_client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = self.config['OpenAI']['ai_model']
        stt = self.config['General']['stt']
        print(f'[INFO] Using {stt} for inference. Model: {self.model}')
        super().__init__(config=self.config,
                         convo=convo,
                         save_to_file=save_to_file,
                         file_name=response_file_name)


class TogetherAIResponder(GPTResponder):
    """Uses TogetherAI for Chat Inference"""

    def __init__(self,
                 config: dict,
                 convo: conversation.Conversation,
                 save_to_file: bool = False,
                 response_file_name: str = 'logs/response.txt'):
        root_logger.info(TogetherAIResponder.__name__)
        self.config = config
        api_key = self.config['Together']['api_key']
        base_url = self.config['Together']['base_url']
        self.llm_client = openai.OpenAI(api_key=api_key,
                                        base_url=base_url)
        self.model = self.config['Together']['ai_model']
        print(f'[INFO] Using Together AI for inference. Model: {self.model}')
        super().__init__(config=self.config,
                         convo=convo,
                         save_to_file=save_to_file,
                         file_name=response_file_name)


class InferenceResponderFactory:
    """Factory class to get the appropriate Inference Provider / GPT Provider
    """
    def get_responder_instance(self,
                               provider: InferenceEnum,
                               config: dict,
                               convo: conversation.Conversation,
                               save_to_file: bool = False,
                               response_file_name: str = 'logs/response.txt'
                               ) -> GPTResponder:
        """Get the appropriate Inference Provider class instance
        Args:
          provider: InferenceEnum: The Inference provider enum
          config: dict: Used to pass all configuration parameters
          convo: Conversation: Conversation object for storing all conversation text
          save_to_file: bool: Save LLM responses to file or not
          response_file_name: str: Filename for saving LLM responses
        """
        if not isinstance(provider, InferenceEnum):
            raise TypeError('InferenceResponderFactory: provider should be an instance of InferenceEnum')

        if provider == InferenceEnum.OPENAI:
            return OpenAIResponder(config=config,
                                   convo=convo,
                                   save_to_file=save_to_file,
                                   response_file_name=response_file_name)
        elif provider == InferenceEnum.TOGETHER:
            return TogetherAIResponder(config=config,
                                       convo=convo,
                                       save_to_file=save_to_file,
                                       response_file_name=response_file_name)
        raise ValueError("Unknown Inference Provider type")


if __name__ == "__main__":
    print('GPTResponder')
