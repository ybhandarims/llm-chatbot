# Settings Service Developer Guide

This service stores user preferences and the system prompt used by the AI.

## What this service does

- Reads and updates the system prompt
- Stores basic user settings
- Shares settings with the gateway and AI worker

## Why it exists

It gives the app one place for prompt and preference changes. That means the AI behavior can be updated without changing the rest of the system.

## One-minute checklist

- Run the service: `uvicorn main:app --reload --port 8001`
- Run tests: `pytest -q tests`
- Lint / sanity check: `python -m compileall .`
- Build image: `docker build -t llm-chatbot/settings:local .`

## Local notes

- Default port: `8001`
- Health check: `GET /health`
- Main file: `main.py`

## Practical tip

If the AI keeps using the wrong prompt, start here before looking at the worker.