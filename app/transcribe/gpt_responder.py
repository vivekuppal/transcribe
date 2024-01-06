import datetime
import time
# import pprint
import openai
import prompts
import conversation
import constants
from tsutils import app_logging as al
from tsutils import duration


root_logger = al.get_logger()


# When we have to get responses from another LLM as well, we will split this class
# into a base and LLM specific class and move the base class to SDK
class GPTResponder:
    """Handles all interactions with openAI LLM / ChatGPT
    """
    # By default we do not ping LLM to get data
    enabled: bool = False

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
        self.llm_client = openai.OpenAI(api_key=self.config['OpenAI']['api_key'])
        self.model = self.config['OpenAI']['ai_model']
        self.save_response_to_file = save_to_file
        self.response_file = file_name

    def generate_response_from_transcript_no_check(self) -> str:
        """Ping LLM to get a suggested response right away.
           Gets a response even if the continuous suggestion option is disabled.
           Updates the conversation object with the response from LLM.
        """
        try:
            root_logger.info(GPTResponder.generate_response_from_transcript_no_check.__name__)
            with duration.Duration(name='OpenAI Chat Completion', screen=False):
                timeout: int = self.config['OpenAI']['request_timeout_seconds']
                temperature: float = self.config['OpenAI']['temperature']
                multiturn_prompt_content = self.conversation.get_merged_conversation(
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

    def create_client(self, api_key: str):
        if self.llm_client is not None:
            self.llm_client.close()
        self.llm_client = openai.OpenAI(api_key=api_key)

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
            print(f'    Role: {item["role"]}')
            print(f'    Content: {item["content"]}')
            print('  }')

        print(']')


if __name__ == "__main__":
    print('GPTResponder')
