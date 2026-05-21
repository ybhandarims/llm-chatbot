from fastapi import FastAPI

app = FastAPI()

_settings = {"system_prompt": "You are a helpful assistant."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/settings")
def get_settings():
    return _settings


@app.post("/settings")
def update_settings(payload: dict):
    _settings.update(payload)
    return _settings
