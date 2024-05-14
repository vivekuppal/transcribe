# OpenAI API Compatible Provider Support #

Transcribe supports all Providers who are API compatible with OpenAI API specification.
- Azure
- Perplexity
- Together

To choose a specific provider add the following section to `override.yaml` file

```
OpenAI:
  api_key: 'PROVIDER_SPECIFIC_API_KEY'
  base_url: 'BASE_URL_FOR_PROVIDER'
  ai_model: 'MODEL_OF_CHOICE'
```

Default `base_url` for OpenAI is `https://api.openai.com/v1`
Default `ai_model` for OpenAI is `gpt-4o`

Our users have found this to be very useful in countries like Australia and China, where they cannot access the default providers directly or it is cost prohibitive to access these providers.
