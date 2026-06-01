# AI Service Developer Guide

This service is responsible for turning conversation context into an assistant reply.

## What this service does

- Reads the latest user message and chat context
- Calls the model provider
- Returns or stores the generated assistant answer

## Why it exists

This is the brains of the system. Separating it from the gateway means you can change the model logic or worker behavior without touching the request router.

## One-minute checklist

- Run the service: `uvicorn main:app --reload --port 8004`
- Run tests: `pytest -q tests`
- Lint / sanity check: `python -m compileall .`
- Build image: `docker build -t llm-chatbot/ai-worker:local .`

## Local notes

- Default port: `8004`
- Health check: `GET /health`
- Main file: `main.py`

## Practical tip

If the model call fails, first check credentials and API access, then inspect the input context passed to the worker.