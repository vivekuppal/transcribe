import sys
from heapq import merge
import datetime
import constants
from db import AppDB as appdb, conversation as convodb
sys.path.append('../..')
from tsutils import configuration  # noqa: E402 pylint: disable=C0413


class Conversation:
    """Encapsulates the complete conversation.
    Has text from Speakers, Microphone, LLM, Instructions to LLM
    """
    _initialized: bool = False

    def __init__(self):
        self.transcript_data = {constants.PERSONA_SYSTEM: [],
                                constants.PERSONA_YOU: [],
                                constants.PERSONA_SPEAKER: [],
                                constants.PERSONA_ASSISTANT: []}
        self.last_update: datetime.datetime = None
        self.initialize_conversation()

    def initialize_conversation(self):
        """Populate initial app data for conversation object
        """
        self.config = configuration.Config().data
        prompt = self.config["General"]["system_prompt"]
        response_lang = self.config["OpenAI"]["response_lang"]
        if response_lang is not None:
            prompt += f'.  Respond exclusively in {response_lang}.'

        self.update_conversation(persona=constants.PERSONA_SYSTEM, text=prompt,
                                 time_spoken=datetime.datetime.utcnow())
        initial_convo: dict = self.config["General"]["initial_convo"]
        # Read the initial conversation from parameters.yaml file and add to the convo
        for _, value in initial_convo.items():
            role = value['role']
            content = value['content']
            self.update_conversation(persona=role, text=content,
                                     time_spoken=datetime.datetime.utcnow())
        self.last_update: datetime.datetime = datetime.datetime.utcnow()
        self._initialized = True

    def clear_conversation_data(self):
        """Clear all conversation data
        """
        self.transcript_data[constants.PERSONA_YOU].clear()
        self.transcript_data[constants.PERSONA_SPEAKER].clear()
        self.transcript_data[constants.PERSONA_SYSTEM].clear()
        self.transcript_data[constants.PERSONA_ASSISTANT].clear()
        self.initialize_conversation()

    def update_conversation(self, persona: str,
                            text: str,
                            time_spoken,
                            update_previous: bool = False):
        """Update conversation with new data
        Args:
        person: person this part of conversation is attributed to
        text: Actual words
        time_spoken: Time at which conversation happened, this is typically reported in local time
        """

        transcript = self.transcript_data[persona]
        convo_id = None

        # DB is not available at the time conversation object is being initialized.
        if self._initialized:
            inv_id = appdb().get_invocation_id()
            engine = appdb().get_engine()
            convo_object: convodb.Conversations = appdb().get_object(convodb.TABLE_NAME)
            convo_id = convo_object.get_max_convo_id(engine=engine)

        # if (persona.lower() == 'assistant'):
        #     print(f'Assistant Transcript length to begin with: {len(transcript)}')
        #     print(f'append: {text}')

        # For persona you, we populate one item from parameters.yaml.
        # Hence do not delete the first item for persona == You
        if (update_previous
            and (
                (persona.lower() == 'you' and len(transcript) > 1)
                or (persona.lower() != 'you' and len(transcript) > 0)
                )):
            prev_element = transcript.pop()
            # Use timestamp of previous element, since it is an update
            time_spoken = prev_element[1]
            if self._initialized:
                # Update DB
                # print(f'Removed: {prev_element}')
                # print(f'Update DB: {inv_id} - {time_spoken} - {persona} - {text}')
                convo_object.update_conversation(inv_id, convo_id, text, engine)
        else:
            if self._initialized:
                # Insert in DB
                # print(f'Add to DB: {inv_id} - {time_spoken} - {persona} - {text}')
                convo_id = convo_object.insert_conversation(inv_id, time_spoken, persona, text, engine)

        new_element = f"{persona}: [{text}]\n\n"
        # print(f'Added: {time_spoken} - {new_element}')
        transcript.append((new_element, time_spoken, convo_id))

        # if (persona.lower() == 'assistant'):
        #    print(f'Assistant Transcript length after completion: {len(transcript)}')
        self.last_update = datetime.datetime.utcnow()

    def get_conversation(self,
                         sources: list = None,
                         length: int = 0) -> list:
        """Get the transcript based on specified sources
        Args:
        sources: Get data from which sources (You, Speaker, Assistant, System)
        length: Get the last length elements from the audio transcript.
                Default value = 0, gives the complete transcript for chosen sources
        reverse: reverse the sort order or keep it in chronological order
        """
        if sources is None:
            sources = [constants.PERSONA_YOU,
                       constants.PERSONA_SPEAKER,
                       constants.PERSONA_ASSISTANT,
                       constants.PERSONA_SYSTEM]

        combined_transcript = list(merge(
            self.transcript_data[constants.PERSONA_YOU][-length:] if constants.PERSONA_YOU in sources else [],
            self.transcript_data[constants.PERSONA_SPEAKER][-length:] if constants.PERSONA_SPEAKER in sources else [],
            self.transcript_data[constants.PERSONA_ASSISTANT][-length:] if constants.PERSONA_ASSISTANT in sources else [],
            self.transcript_data[constants.PERSONA_SYSTEM][-length:] if constants.PERSONA_SYSTEM in sources else [],
            key=lambda x: x[1]))
        combined_transcript = combined_transcript[-length:]
        return "".join([t[0] for t in combined_transcript])

    def get_merged_conversation_summary(self, length: int = 0) -> list:
        """Creates a prompt to be sent to LLM (OpenAI by default) for summarizing 
           the conversation.
           length: Get the last length elements from the audio transcript.
           Initial system prompt is always part of the return value
           Default value = 0, gives the complete transcript
        """

        combined_transcript = self.transcript_data[constants.PERSONA_YOU][-length:] \
            + self.transcript_data[constants.PERSONA_SPEAKER][-length:] \
            + self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
        sorted_transcript = sorted(combined_transcript, key=lambda x: x[1])
        sorted_transcript = sorted_transcript[-length:]
        sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_YOU][0])
        sorted_transcript.insert(0, (f"{constants.PERSONA_SYSTEM}: [{self.config['General']['summary_prompt']}]\n\n",
                                     datetime.datetime.now(), -1))
        return sorted_transcript

    def get_merged_conversation_response(self, length: int = 0) -> list:
        """Creates a prompt to be sent to LLM (OpenAI by default) to get
           a contextual response.
           length: Get the last length elements from the audio transcript.
           Initial summary prompt is always part of the return value
           Default value = 0, gives the complete transcript
        """

        combined_transcript = self.transcript_data[constants.PERSONA_YOU][-length:] \
            + self.transcript_data[constants.PERSONA_SPEAKER][-length:] \
            + self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
        sorted_transcript = sorted(combined_transcript, key=lambda x: x[1])
        sorted_transcript = sorted_transcript[-length:]
        sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_YOU][0])
        sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_SYSTEM][0])
        # print(f'{datetime.datetime.now()}: Sorted transcript')
        # self._pretty_print_transcript(sorted_transcript)

        return sorted_transcript

    def _pretty_print_transcript(self, message: list):
        """Format the openAI request in a nice print format"""
        print('[')
        for item in message:
            print('  {')
            print(f'    {item[0].strip()}')
            print(f'    {item[1]}')
            print('  }')

        print(']')
