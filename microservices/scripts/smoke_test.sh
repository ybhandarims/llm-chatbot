#!/usr/bin/env bash
set -e
echo "Waiting for services to come up..."
sleep 3
echo "Create a conversation via gateway"
curl -s -X POST http://localhost:8080/api/conversations -H 'Content-Type: application/json' -d '{"title":"demo"}' | jq || true
echo
echo "Generate a response via gateway"
curl -s -X POST http://localhost:8080/api/generate -H 'Content-Type: application/json' -d '{"prompt":"Hello from smoke test"}' | jq || true
echo
echo "List conversations via gateway"
curl -s http://localhost:8080/api/conversations | jq || true
