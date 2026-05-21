from fastapi import FastAPI, HTTPException
import os
from openai import OpenAI

app = FastAPI()

# Load configuration from env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_MOCK = os.getenv("OPENAI_MOCK", "false").lower() == "true"
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")

client = None
if not OPENAI_MOCK:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required when OPENAI_MOCK=false")
    client = OpenAI(api_key=OPENAI_API_KEY)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate(payload: dict):
    prompt = payload.get("prompt", "")

    if OPENAI_MOCK:
        response = {"text": f"Echo: {prompt}", "model": "local-mock"}
        return {"response": response}

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.2,
        )

        choice = resp.choices[0]
        text = None
        if hasattr(choice, "message") and choice.message is not None:
            text = choice.message.content
        else:
            text = getattr(choice, "text", None) or (resp.get("output_text") if isinstance(resp, dict) else str(resp))

        return {"response": {"text": text, "model": OPENAI_MODEL}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
