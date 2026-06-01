# Gateway Service Developer Guide

The gateway is the front door for the app. It receives requests from the frontend, calls the other services, and returns one joined response.

## What this service does

- Accepts chat and settings API requests
- Routes calls to the settings, conversations, and messages services
- Pushes async AI jobs into SQS in production

## Why it exists

Think of it like a receptionist. The frontend only talks to one place, and the gateway forwards requests to the right service. That keeps the browser simple and the backend easier to change.

## One-minute checklist

- Run the service: `uvicorn main:app --reload --port 8080`
- Run tests: `pytest -q tests`
- Lint / sanity check: `python -m compileall .`
- Build image: `docker build -t llm-chatbot/gateway:local .`

## Local notes

- Default port: `8080`
- Health check: `GET /health`
- Main file: `main.py`

## Practical tip

If the gateway cannot reach another service, the problem is usually the service URL environment variable or the other service not being up yet.