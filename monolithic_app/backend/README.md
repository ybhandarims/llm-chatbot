# Monolithic Backend

FastAPI backend for the first video (monolithic architecture).

## Run

1. Create and activate a virtual environment.
2. Install dependencies.
3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
4. Start server.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

If you want local demo mode without OpenAI calls, set `OPENAI_MOCK=true`.
