# Messages Service Developer Guide

This service stores the actual chat messages for each conversation.

## What this service does

- Saves user messages
- Saves assistant replies
- Returns the latest messages for a conversation

## Why it exists

Messages are the raw transcript of the chat. Keeping them in a separate service makes it easier to scale and query without mixing them with conversation metadata.

## One-minute checklist

- Run the service: `uvicorn main:app --reload --port 8003`
- Run tests: `pytest -q tests`
- Lint / sanity check: `python -m compileall .`
- Build image: `docker build -t llm-chatbot/messages:local .`

## Local notes

- Default port: `8003`
- Health check: `GET /health`
- Main file: `main.py`

## Practical tip

If replies are not showing up, check the gateway request path first, then confirm this service is receiving and saving records.