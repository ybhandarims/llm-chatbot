# Frontend Developer Guide

This folder contains the browser app that users interact with.

## What this app does

- Renders the chat UI
- Sends requests to the gateway
- Displays conversations and assistant replies
- Runs browser-level smoke tests

## Why it exists

This is the screen people actually see. It keeps the user experience separate from backend logic, so the UI can evolve without rewriting services.

## One-minute checklist

- Run the app: `npm start`
- Run tests: `npm test`
- Generate JUnit reports: `npm run test:reports`
- Build image: `docker build -t llm-chatbot/frontend:local .`

## Local notes

- Default port: `3000`
- Static entry point: `public/index.html`
- Main app script: `public/assets/app.js`

## Practical tip

If the UI loads but data is empty, check whether the gateway is running and whether the frontend is pointing at the correct API base URL.