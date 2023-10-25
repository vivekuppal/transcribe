import datetime
import time
import pprint
import openai
import GlobalVars
import prompts
import conversation
import constants
import configuration
import app_logging as al
import duration


root_logger = al.get_logger()


class GPTResponder:
    """Handles all interactions with openAI LLM / ChatGPT
    """
    def __init__(self, convo: conversation.Conversation,
                 save_to_file: bool = False,
                 file_name: str = 'response.txt'):
        root_logger.info(GPTResponder.__name__)
        self.response = prompts.INITIAL_RESPONSE
        self.response_interval = 2
        self.gl_vars = GlobalVars.TranscriptionGlobals()
        openai.api_key = self.gl_vars.api_key
        self.conversation = convo
        self.config = configuration.Config().data
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
            # print(f'{datetime.datetime.now()} - {GPTResponder.generate_response_from_transcript_no_check.__name__}')
            with duration.Duration(name='OpenAI Chat Completion', screen=True):
                multiturn_prompt_content = self.conversation.get_merged_conversation(
                    length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
                multiturn_prompt_api_message = prompts.create_multiturn_prompt(multiturn_prompt_content)
                # print(f'Multiturn prompt for ChatGPT: {multiturn_prompt_api_message}')
                # Multi turn response is only effective when continuous mode is off.
                # In continuous mode, there are far too many responses from LLM,
                # they confuse the LLM if that many responses are replayed back to LLM.
                # print(f'{datetime.datetime.now()} - Request response')
                # self._pretty_print_openai_request(multiturn_prompt_api_message)
                multi_turn_response = openai.ChatCompletion.create(
                        model=self.model,
                        messages=multiturn_prompt_api_message,
                        temperature=0.0,
                        request_timeout=10
                )
                # pprint.pprint(f'openai response: {multi_turn_response}', width=120)
                # print(f'{datetime.datetime.now()} - Got response')

        except Exception as exception:
            print(exception)
            root_logger.error('Error when attempting to get a response from LLM.')
            root_logger.exception(exception)
            return prompts.INITIAL_RESPONSE

        multi_turn_response_content = multi_turn_response.choices[0].message.content
        try:
            # pprint.pprint(f'Multi turn response: {multi_turn_response_content}')
            processed_multi_turn_response = self.process_response(multi_turn_response_content)
            self.update_conversation(persona=constants.PERSONA_ASSISTANT,
                                     response=processed_multi_turn_response)
        except Exception as exception:
            root_logger.error('Error parsing response from LLM.')
            root_logger.exception(exception)
            return prompts.INITIAL_RESPONSE

        if self.save_response_to_file:
            with open(file=self.response_file, mode="a", encoding='utf-8') as f:
                f.write(f'{datetime.datetime.now()} - {processed_multi_turn_response}\n')

        return processed_multi_turn_response

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

    def generate_response_from_transcript(self, transcript):
        """Ping OpenAI LLM model to get response from the Assistant
        """
        root_logger.info(GPTResponder.generate_response_from_transcript.__name__)
        if self.gl_vars.freeze_state[0]:
            return ''

        return self.generate_response_from_transcript_no_check()

    def update_conversation(self, response, persona):
        root_logger.info(GPTResponder.update_conversation.__name__)
        if response != '':
            self.response = response
            self.conversation.update_conversation(persona=persona,
                                                  text=response,
                                                  time_spoken=datetime.datetime.utcnow())

    def respond_to_transcriber(self, transcriber):
        """Thread method to continously update the transcript
        """
        while True:

            if transcriber.transcript_changed_event.is_set():
                start_time = time.time()

                transcriber.transcript_changed_event.clear()

                # Do processing only if LLM transcription is enabled
                if not self.gl_vars.freeze_state[0]:
                    transcript_string = transcriber.get_transcript(
                        length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
                    self.generate_response_from_transcript(transcript_string)

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
