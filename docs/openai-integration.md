# OpenAI API setup reference

The backend loads the project-root `.env` through `backend/app/config.py`. This project uses the instructor's custom `OPEN_AI` variable, so `backend/app/controllers/openai_client.py` reads that value and passes it explicitly as `OpenAI(api_key=api_key)`. The OpenAI SDK's default environment name is `OPENAI_API_KEY`; do not rely on that default for this project.

The configured model is read from `OPENAI_MODEL`, defaulting to `gpt-6-luna`. A read-only request to `/v1/models` using the configured key confirmed that model is currently available to this account. Its standard short-context text rates are $0.10 per million input tokens and $0.50 per million output tokens; cached input is $0.01 per million. Current pricing can change, so check the live pricing page before use. The API `/models` endpoint lists models available to the authenticated account.

## Adapted reference example

The official Python SDK pattern is to create an `OpenAI` client and call `client.responses.create(...)`. `backend/app/controllers/rag.py` adapts it as two requests: the first proposes SQL from the saved-hotel schema, and the second grounds a response in the original question, validated SQL, and bounded SQLite rows. The service never sends credentials, users, bookings, or the full database to the model.

```python
client = create_openai_client()
if client is None:
    raise RuntimeError("OpenAI API key is not configured.")

response = client.responses.create(
    model=OPENAI_MODEL,
    input="Question, schema, and rules for the SQL proposal request.",
)
```

The generated query is executed with SQLite read-only mode, an authorizer restricted to `saved_hotels`, `saved_hotel_zips`, and `demo_hotel_nights`, a time budget, and a 20-row cap. A second call receives only the question, validated SQL, and returned rows.

Keep credentials in the ignored project-root `.env`. The health response reports only whether a key is configured and the model name; it never returns the key. Never put the key in Vue code, screenshots, committed files, or prompts.

Reference: [OpenAI Python SDK](https://developers.openai.com/api/reference/python), [Models](https://developers.openai.com/api/docs/models), [Pricing](https://developers.openai.com/api/docs/pricing).
