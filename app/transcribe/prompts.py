# import pprint
from global_vars import TranscriptionGlobals, T_GLOBALS


INITIAL_RESPONSE = '👋 Welcome to Transcribe 🤝'
global_vars_module: TranscriptionGlobals = T_GLOBALS


def create_prompt_for_text(text: str, config: dict):
    """Get a prompt for the selected text
    """
    if text is None or text == '':
        return None
    complete_prompt = f'{config["General"]["default_prompt_preamble"]} '\
        f'{text}'\
        f'{config["General"]["default_prompt_epilogue"]}'
    messages = [{"role": "system", "content": complete_prompt}]
    return messages


def create_multiturn_prompt(convo: list[tuple]) -> list[dict[str, str]]:
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
    # Each convo item is a tuple
    for convo_item in convo:
        # print(convo_item)
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
