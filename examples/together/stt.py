from openai import OpenAI


TOGETHER_API_KEY = 'API_KEY'
# Supported models are at - https://docs.together.ai/docs/inference-models


client = OpenAI(api_key=TOGETHER_API_KEY, base_url='https://api.together.xyz')

chat_completion = client.chat.completions.create(
  messages=[
    {
      'role': 'system',
      'content': 'You are an AI assistant',
    },
    {
      'role': 'user',
      'content': 'Tell me about Fantasy Football',
    }
  ],
  model='mistralai/Mixtral-8x7B-Instruct-v0.1',
  max_tokens=1024
)

print(chat_completion.choices[0].message.content)
