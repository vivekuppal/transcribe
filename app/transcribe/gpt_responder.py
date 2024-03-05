import datetime
import time
from enum import Enum
# import pprint
import openai
import prompts
import conversation
import constants
from tsutils import app_logging as al
from tsutils import duration


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
                 file_name: str = 'logs/response.txt'):
        root_logger.info(GPTResponder.__name__)
        # This var is used by UI to populate the response textbox
        self.response = prompts.INITIAL_RESPONSE
        self.response_interval = 2
        self.conversation = convo
        self.config = config
        self.save_response_to_file = save_to_file
        self.response_file = file_name

    def summarize(self) -> str:
        """Ping LLM to get a summary of the conversation.
        """
        root_logger.info(GPTResponder.summarize.__name__)

        if self.config['OpenAI']['api_key'] in ('', 'API_KEY'):
            # Cannot summarize without connection to LLM
            return None

        with duration.Duration(name='OpenAI Summarize', screen=False):
            timeout: int = self.config['OpenAI']['summarize_request_timeout_seconds']
            temperature: float = self.config['OpenAI']['temperature']
            prompt_content = self.conversation.get_merged_conversation_summary()
            prompt_api_message = prompts.create_multiturn_prompt(prompt_content)
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

        return collected_messages

    def generate_response_from_transcript_no_check(self) -> str:
        """Ping LLM to get a suggested response right away.
           Gets a response even if the continuous suggestion option is disabled.
           Updates the conversation object with the response from LLM.
        """
        try:
            root_logger.info(GPTResponder.generate_response_from_transcript_no_check.__name__)
            if self.config['OpenAI']['api_key'] in ('', 'API_KEY'):
                return None

            with duration.Duration(name='OpenAI Chat Completion', screen=False):
                timeout: int = self.config['OpenAI']['response_request_timeout_seconds']
                temperature: float = self.config['OpenAI']['temperature']
                multiturn_prompt_content = self.conversation.get_merged_conversation_response(
                    length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
                multiturn_prompt_api_message = prompts.create_multiturn_prompt(
                    multiturn_prompt_content)
                # Multi turn response is very effective when continuous mode is off.
                # In continuous mode, there are far too many responses from LLM.
                # They can confuse the LLM if that many responses are replayed back to LLM.
                # print(f'{datetime.datetime.now()} - Request response')
                # self._pretty_print_openai_request(multiturn_prompt_api_message)
                multi_turn_response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=multiturn_prompt_api_message,
                    temperature=temperature,
                    timeout=timeout,
                    stream=True
                )
                # pprint.pprint(f'openai response: {multi_turn_response}', width=120)
                # print(f'{datetime.datetime.now()} - Got response')

                # Update conversation with an empty response. This response will be updated
                # by subsequent updates from the streaming response
                self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                          response="  ", pop=False)
                collected_messages = ""
                for chunk in multi_turn_response:
                    chunk_message = chunk.choices[0].delta  # extract the message
                    if chunk_message.content:
                        message_text = chunk_message.content
                        collected_messages += message_text
                        # print(f"{message_text}", end="")
                        self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                                  response=collected_messages, pop=True)

        except Exception as exception:
            print('Error when attempting to get a response from LLM.')
            print(exception)
            root_logger.error('Error when attempting to get a response from LLM.')
            root_logger.exception(exception)
            return prompts.INITIAL_RESPONSE

        processed_multi_turn_response = collected_messages

        if self.save_response_to_file:
            with open(file=self.response_file, mode="a", encoding='utf-8') as f:
                f.write(f'{datetime.datetime.now()} - {processed_multi_turn_response}\n')

        return processed_multi_turn_response

    def create_client(self, api_key: str, base_url: str = None):
        if self.llm_client is not None:
            self.llm_client.close()
        self.llm_client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def process_response(self, input_str: str) -> str:
        """ Extract relevant data from LLM response.
        """
        lines = input_str.split(sep='\n')
        response = ''
        for line in lines:
            # Skip any responses that contain content like
            # Speaker 1: <Some statement>
            # This is generated content added by OpenAI that can be skipped
            if 'Speaker' in line and ':' in line:
                continue
            response = response + line.strip().strip('[').strip(']')

        return response

    def generate_response_from_transcript(self) -> str:
        """Ping OpenAI LLM model to get response from the Assistant
        """
        root_logger.info(GPTResponder.generate_response_from_transcript.__name__)

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
            if self.config['OpenAI']['api_key'] in ('', 'API_KEY'):
                return None

            with duration.Duration(name='OpenAI Chat Completion Selected', screen=False):
                timeout: int = self.config['OpenAI']['response_request_timeout_seconds']
                temperature: float = self.config['OpenAI']['temperature']
                prompt = prompts.create_prompt_for_text(text=text)
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
                                          response="  ", pop=False)
                collected_messages = ""
                for chunk in llm_response:
                    chunk_message = chunk.choices[0].delta  # extract the message
                    if chunk_message.content:
                        message_text = chunk_message.content
                        collected_messages += message_text
                        # print(f"{message_text}", end="")
                        self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                                  response=collected_messages, pop=True)

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

    def _update_conversation(self, response, persona, pop=False):
        """Update the internaal conversation state"""
        root_logger.info(GPTResponder._update_conversation.__name__)
        if response != '':
            self.response = response
            self.conversation.update_conversation(persona=persona,
                                                  text=response,
                                                  time_spoken=datetime.datetime.utcnow(),
                                                  pop=pop)

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

                remaining_time = self.response_interval - execution_time
                if remaining_time > 0:
                    time.sleep(remaining_time)
            else:
                time.sleep(self.response_interval)

    def update_response_interval(self, interval):
        """Change the interval for pinging LLM
        """
        root_logger.info(GPTResponder.update_response_interval.__name__)
        self.response_interval = interval

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
        print(f'[INFO] Using OpenAI for inference. Model: {self.model}')
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
        print(f'[INFO] Using Together for inference. Model: {self.model}')
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
