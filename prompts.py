# import datetime
# import pprint
import configuration

INITIAL_RESPONSE = '👋 Welcome to Transcribe 🤝'


def create_prompt(transcript):
    config = configuration.Config().get_data()
    preamble = config["OpenAI"]["default_prompt_preamble"]
    epilogue = config["OpenAI"]["default_prompt_epilogue"]
    return f'{preamble} \
 \
{transcript}.\
{epilogue}'


def create_single_turn_prompt_message(transcript: str) -> list:
    """Create message list to be sent to LLM.
       Creates a single item in the list in the format
            [{
                role: system
                content: <Prompt Message>
            }]
       The single message contains everything including system prompt and user input
    """
    config = configuration.Config().get_data()
    response_lang = config["OpenAI"]["response_lang"]
    preamble = config["OpenAI"]["default_prompt_preamble"]
    epilogue = config["OpenAI"]["default_prompt_epilogue"]
    message = f'{preamble} \
 \
{transcript}.\
{epilogue} Respond exclusively in {response_lang}.'

    prompt_api_message = [{"role": "system", "content": message}]
    return prompt_api_message


def create_multiturn_prompt(convo: list) -> list:
    """Create message list to be sent to LLM.
       Creates multiple items in the list in the format
            [
                {
                    role: system
                    content: <Prompt Message>
                }
                {
                    role: user
                    content:<text input from user>
                }
                {
                    role: assistant
                    content:<Any previous responses from LLM assistant>
                }
            ]
       The single message contains everything including system prompt and user input
    """
    ret_value = []

    for convo_item in convo:
        # Get Persona, text
        convo_persona = convo_item[0][0:convo_item[0].find(':')]
        # print(convo_persona)
        if convo_persona.lower() == 'you' or convo_persona.lower() == 'speaker':
            convo_persona = 'user'
        convo_content = convo_item[0][convo_item[0].find(':')+1:]
        # strip whitespace in the beginning, end
        convo_content = convo_content.strip()
        # remove square brackets
        convo_content = convo_content[1:-1]
        # print(convo_content)
        ret_value.append({"role": convo_persona, "content": convo_content})

    # pprint.pprint(ret_value)
    return ret_value
