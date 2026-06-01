# Conversations Service Developer Guide

This service stores conversation records, titles, and history metadata.

## What this service does

- Creates conversations
- Updates conversation metadata
- Returns the message history for a conversation

## Why it exists

It keeps the chat timeline organized. Instead of one giant database table for everything, this service owns the conversation layer and makes it easier to grow later.

## One-minute checklist

- Run the service: `uvicorn main:app --reload --port 8002`
- Run tests: `pytest -q tests`
- Lint / sanity check: `python -m compileall .`
- Build image: `docker build -t llm-chatbot/conversations:local .`

## Local notes

- Default port: `8002`
- Health check: `GET /health`
- Main file: `main.py`

## Practical tip

If test data looks missing, check whether the local database file or mounted volume was reset.