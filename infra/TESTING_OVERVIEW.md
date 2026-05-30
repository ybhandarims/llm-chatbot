# Testing Overview for llm-chatbot

This document describes the automated tests currently present in the repository, what each test checks, where the tests live, the results observed locally, and how to run them locally and in CI.

## CI workflow
- Workflow file: [.github/workflows/microservices-unit-tests.yml](.github/workflows/microservices-unit-tests.yml)
- What it runs:
  - Python tests: runs `pytest` for each Python microservice found in `microservices/<service>/tests` (matrix job named `python-unit-tests`).
  - Frontend tests: runs `npm test` in `microservices/frontend` (job `frontend-unit-tests`).

Triggering: the workflow runs on `push`, `pull_request` (paths limited to `microservices/**` and the workflow file), and can be manually triggered via `workflow_dispatch`.

## Tests available now (summary)

- Python microservice health/unit checks (fast)
  - Location: [microservices/ai-service/tests/test_health.py](microservices/ai-service/tests/test_health.py)
  - Location: [microservices/gateway/tests/test_health.py](microservices/gateway/tests/test_health.py)
  - Location: [microservices/conversations-service/tests/test_health.py](microservices/conversations-service/tests/test_health.py)
  - Location: [microservices/messages-service/tests/test_health.py](microservices/messages-service/tests/test_health.py)
  - Location: [microservices/settings-service/tests/test_health.py](microservices/settings-service/tests/test_health.py)
  - Purpose: Minimal unit/health tests that import the service entrypoint and assert the `/health` handler returns the expected structure. These are fast smoke/unit tests intended to catch obvious import/runtime errors and verify the app exposes a health endpoint.
  - Local result: all health tests passed locally (each service reported 1 test passed).

- Conversations-service API tests (integration-style, in-memory/mocked DB)
  - Location: [microservices/conversations-service/tests/test_api.py](microservices/conversations-service/tests/test_api.py)
  - Purpose: Uses FastAPI `TestClient` to exercise the service's HTTP endpoints: create conversation, get conversation, append message, list conversations, and delete conversation. The test replaces the real DynamoDB table object with an in-memory fake (`FakeTable`) so tests run quickly without external AWS access.
  - Test type: API / integration-style (application-level) but still lightweight because it runs in-process and mocks external resources.
  - Local result: passed (2 tests passed when run locally; see terminal run where the test executed successfully).

- Frontend DOM tests (JSDOM)
  - Files:
    - [microservices/frontend/tests/smoke.test.js](microservices/frontend/tests/smoke.test.js) — trivial smoke check
    - [microservices/frontend/tests/app.test.js](microservices/frontend/tests/app.test.js) — UI bootstrap + conversations/messages render test
    - [microservices/frontend/tests/form.test.js](microservices/frontend/tests/form.test.js) — form submit test: simulates typing and submits the chat form and asserts UI updates
  - Purpose: Simulate browser DOM (via JSDOM) to verify the static SPA's bootstrap sequence, rendering of conversation list and messages, and the behavior of the chat form. These tests mock network calls (`window.fetch`) and inline `public/assets/app.js` into the DOM during the test so JSDOM doesn't make real HTTP requests.
  - Test type: UI / DOM-level unit/integration tests that run in Node (headless, no real browser). They validate client-side logic, DOM updates, and integration points with the API via mocked fetch responses.
  - Local result: all frontend tests passed locally (3 tests passed).

## Which tests run where (short)

- Local commands you ran:
  - Python tests: `python -m pytest microservices/<service>/tests -q` (or via project's venv python)
  - Frontend tests: `cd microservices/frontend && npm test` (runs Node's `node --test tests/*.test.js`)

- CI (GitHub Actions) runs the same commands in the workflow:
  - Python: `pip install -r <service>/requirements.txt pytest` then `pytest <service>/tests -q`
  - Frontend: `npm install` then `npm test` in `microservices/frontend`

## Classification: unit vs integration vs UI

- Unit tests: small, fast tests verifying single functions or minimal endpoints without network or DB dependencies. Example: the simple `test_health.py` files.
- Integration/API tests: exercise the HTTP endpoints and behaviors of the service in-process; they may mock external resources (DynamoDB). Example: `conversations-service/tests/test_api.py`.
- UI/DOM tests: run in Node using JSDOM to simulate a browser and verify client-side rendering and behavior. Examples: `app.test.js`, `form.test.js`, `smoke.test.js`.

## How to run tests locally (copyable commands)

1) Using the repository virtual environment (recommended) — from repo root:

```powershell
# Windows PowerShell (use the venv Python reported by the project)
& "./.venv/Scripts/python.exe" -m pip install -r microservices/conversations-service/requirements.txt pytest
& "./.venv/Scripts/python.exe" -m pytest microservices/conversations-service/tests -q
```

2) Run tests for all Python services quickly (one-by-one):

```bash
python -m pytest microservices/ai-service/tests -q
python -m pytest microservices/gateway/tests -q
python -m pytest microservices/conversations-service/tests -q
python -m pytest microservices/messages-service/tests -q
python -m pytest microservices/settings-service/tests -q
```

3) Frontend tests (Node):

```bash
cd microservices/frontend
npm install
npm test
```

Notes: Frontend tests use `jsdom` and inline `public/assets/app.js` during testing to avoid network fetches. If you change the SPA bootstrap, update tests to reflect new DOM IDs or event wiring.

## CI behavior and tips

- The workflow file is [.github/workflows/microservices-unit-tests.yml](.github/workflows/microservices-unit-tests.yml). When you push changes under `microservices/**`, GitHub Actions will run the workflow and execute the same test commands described above.
- If some tests are slow or require external resources (real DynamoDB, external APIs), either:
  - Mock those dependencies (preferred), or
  - Move slow/integration tests to a separate workflow that runs on `main` only, not on every PR.

## Troubleshooting common failures

- JSDOM network errors (ECONNREFUSED): caused by `index.html` linking `/assets/app.js` or `/assets/styles.css` which JSDOM tries to fetch. Fixes:
  - Inline `app.js` in the test (we already do this), or
  - Provide a resource loader stub, or serve files via a local static server during tests.
- DynamoDB/boto3 errors in tests: mock the `table` object or use localstack/moto. The conversations-service API test uses an in-memory `FakeTable` to avoid real AWS calls.

## Where to look / files changed by recent work
- CI workflow: [.github/workflows/microservices-unit-tests.yml](.github/workflows/microservices-unit-tests.yml)
- Conversations API tests: [microservices/conversations-service/tests/test_api.py](microservices/conversations-service/tests/test_api.py)
- Python health tests: see each service under `microservices/*/tests/test_health.py` (AI/gateway/conversations/messages/settings)
- Frontend tests: [microservices/frontend/tests/app.test.js](microservices/frontend/tests/app.test.js), [microservices/frontend/tests/form.test.js](microservices/frontend/tests/form.test.js), [microservices/frontend/tests/smoke.test.js](microservices/frontend/tests/smoke.test.js)

## Next improvements (suggestions)
- Split very small fast unit tests from slower integration tests in CI using separate job labels (e.g., `unit` vs `integration`).
- Add test reporting (JUnit XML) for GitHub Actions to surface failures in the Actions UI.
- Add coverage collection to measure test coverage per service.

---
If you want, I can:
- Mark each existing test as `unit` or `integration` and adjust the workflow to run only units on PRs.
- Add JUnit-style test reporting to the workflow.
- Add a separate `integration-tests.yml` workflow that runs slower integration tests on `main`.

Tell me which option you prefer and I will implement it.
