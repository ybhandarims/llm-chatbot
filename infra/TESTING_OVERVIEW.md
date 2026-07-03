# Testing Overview for llm-chatbot

This document describes the automated tests currently present in the repository, what each test checks, where the tests live, the results observed locally, and how to run them locally and in CI.

## CI workflow
 - Workflow file: [.github/workflows/ci.yml](.github/workflows/ci.yml)
 - What it runs:
   - Python tests: uses [microservices/scripts/full_test_pass.py](microservices/scripts/full_test_pass.py), which runs the six-service backend test pass from the repo root.
   - Frontend tests: runs the Node test reporter in `microservices/frontend` and writes JUnit XML for the workflow artifact.
 - Triggering: the workflow runs on `push` and `pull_request` to `main` or `release/**`, and it can be started manually with `workflow_dispatch`.
 - Path filters: only runs when `microservices/**`, `infra/**`, or `.github/workflows/**` change.

Plain-language summary: this workflow is the main “check the code, build the app, then deploy it” pipeline. A push or PR starts the checks automatically, and a manual trigger lets you rerun the same pipeline when you need to debug GitHub Actions.

## Plain-language summary (what we changed and what runs in CI)

- What we added recently:
  - a GitHub Actions workflow under `.github/workflows/ci.yml` to run the repo-wide test pass, build images, push to ECR, and deploy with Helm;
  - minimal unit/health tests for each Python microservice so CI fails fast on broken imports or missing endpoints;
  - an API-level test for the `conversations-service` that exercises create/get/append/list/delete flows using an in-memory fake DynamoDB table;
  - a frontend DOM-level test (JSDOM) that simulates the browser, submits the chat form, and asserts the UI updates.

- In very simple terms — which tests run where:
  - GitHub Actions (CI) now runs the same backend sequence we use locally through `microservices/scripts/full_test_pass.py`, then runs the frontend test reporter in `microservices/frontend`.
  - So: the CI job first checks the Python services, then checks the browser-side frontend behavior, and only after that does the build-and-deploy job continue.

If you prefer CI to separate very-fast unit tests from slower API/integration tests, I can split those into separate jobs (units on PRs, integrations on main).

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
  - Python tests: `python microservices/scripts/full_test_pass.py` for the repo-wide pass, or `python -m pytest microservices/<service>/tests -q` for a single service
  - Frontend tests: `cd microservices/frontend && npm test` (runs Node's `node --test tests/*.test.js`)
  - Frontend JUnit reports: `cd microservices/frontend && npm run test:reports` to generate `reports/frontend-tests.xml`

- CI (GitHub Actions) runs the same commands in the workflow:
  - Python: `python microservices/scripts/full_test_pass.py`
  - Frontend: `npm ci` then the Node JUnit reporter in `microservices/frontend`

## Classification: unit vs integration vs UI

- Unit tests: small, fast tests verifying single functions or minimal endpoints without network or DB dependencies. Example: the simple `test_health.py` files.
- Integration/API tests: exercise the HTTP endpoints and behaviors of the service in-process; they may mock external resources (DynamoDB). Example: `conversations-service/tests/test_api.py`.
- UI/DOM tests: run in Node using JSDOM to simulate a browser and verify client-side rendering and behavior. Examples: `app.test.js`, `form.test.js`, `smoke.test.js`.

## How to run tests locally (copyable commands)

1) One-command full 7-service pass — from repo root:

PowerShell (Windows):

```powershell
# Create the repo venv if missing, then activate it and run
if (-Not (Test-Path .\.venv\Scripts\Activate.ps1)) {
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python microservices/scripts/full_test_pass.py
```

Bash (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python microservices/scripts/full_test_pass.py
```

2) Using the repository virtual environment for a single service (recommended) — from repo root:

PowerShell (Windows):

```powershell
# create venv if missing, then activate it and install requirements
if (-Not (Test-Path .\.venv\Scripts\Activate.ps1)) {
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r microservices/conversations-service/requirements.txt pytest
python -m pytest microservices/conversations-service/tests -q
```

Bash (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r microservices/conversations-service/requirements.txt pytest
python -m pytest microservices/conversations-service/tests -q
```

3) Run tests for all Python services quickly (one-by-one):

```bash
python -m pytest --import-mode=importlib microservices/ai-service/tests/test_health.py microservices/gateway/tests/test_health.py microservices/conversations-service/tests/test_health.py microservices/conversations-service/tests/test_api.py microservices/messages-service/tests/test_health.py microservices/settings-service/tests/test_health.py -q
```

4) Frontend tests (Node):

Note: the frontend test runner uses `node --test` and requires Node.js 18 or newer. If you have an older Node.js installed, upgrade Node or use `npm run test:reports` after installing dependencies.

```bash
cd microservices/frontend
npm install
npm test
```

Notes: Frontend tests use `jsdom` and inline `public/assets/app.js` during testing to avoid network fetches. If you change the SPA bootstrap, update tests to reflect new DOM IDs or event wiring.

## CI behavior and tips

- The workflow file is [.github/workflows/ci.yml](.github/workflows/ci.yml). When you push changes under `microservices/**`, `infra/**`, or `.github/workflows/**`, GitHub Actions will run the workflow and execute the same test commands described above.
- If some tests are slow or require external resources (real DynamoDB, external APIs), either:
  - Mock those dependencies (preferred), or
  - Move slow/integration tests to a separate workflow that runs on `main` only, not on every PR.

## Recent CI note

- On 2026-05-31, the `Microservices Unit Tests` workflow run passed, but the `Integration Tests (main)` workflow run failed on the conversations-service report step.
- I reran `microservices/conversations-service/tests/test_api.py` locally and it passed, and the generated JUnit XML reported `failures="0"`.
- For now, treat that integration failure as CI-specific until the failing artifact or GitHub Actions log shows a reproducible assertion error.

## Troubleshooting common failures

- JSDOM network errors (ECONNREFUSED): caused by `index.html` linking `/assets/app.js` or `/assets/styles.css` which JSDOM tries to fetch. Fixes:
  - Inline `app.js` in the test (we already do this), or
  - Provide a resource loader stub, or serve files via a local static server during tests.
- DynamoDB/boto3 errors in tests: mock the `table` object or use localstack/moto. The conversations-service API test uses an in-memory `FakeTable` to avoid real AWS calls.

## Where to look / files changed by recent work
- CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)
- Test-only workflows: [.github/workflows/microservices-unit-tests.yml](.github/workflows/microservices-unit-tests.yml) and [.github/workflows/integration-tests.yml](.github/workflows/integration-tests.yml)
- Conversations API tests: [microservices/conversations-service/tests/test_api.py](microservices/conversations-service/tests/test_api.py)
- Python health tests: see each service under `microservices/*/tests/test_health.py` (AI/gateway/conversations/messages/settings)
- Frontend tests: [microservices/frontend/tests/app.test.js](microservices/frontend/tests/app.test.js), [microservices/frontend/tests/form.test.js](microservices/frontend/tests/form.test.js), [microservices/frontend/tests/smoke.test.js](microservices/frontend/tests/smoke.test.js)

## Next improvements (suggestions)
- Split very small fast unit tests from slower integration tests in CI using separate job labels (e.g., `unit` vs `integration`).
- Add test reporting (JUnit XML) for GitHub Actions to surface failures in the Actions UI.
- Add coverage collection to measure test coverage per service.

---
## Pytest markers & selective runs

You can tag slower integration tests with pytest markers and run subsets locally or in CI.

- Mark an integration test:

```python
import pytest

@pytest.mark.integration
def test_long_running_flow():
  ...
```

- Run only integration tests:

```bash
pytest -m integration
```

- Run only unit tests (exclude integration):

```bash
pytest -m "not integration"
```

This makes it easy to keep PR workflows fast while running full suites on `main`.

## CI artifacts — a plain-language guide (where to find test reports and what they mean)

If you're not familiar with CI artifacts and JUnit reports, here's a simple, step-by-step explanation in plain language.

- What a coverage report is:
  - A coverage report shows how much of the code was exercised by the tests that ran in GitHub Actions.
  - The XML report is machine-readable (`reports/<service>-coverage.xml`) and the HTML report is easier to inspect in a browser (`reports/<service>-htmlcov/`).
  - Higher coverage means more lines of code were touched by tests, but it does not automatically mean the code is fully correct.

- What happens when CI runs tests:
  - Each workflow job (for example the Python unit job or the frontend job) runs the test commands and writes a small report file describing which tests passed and which failed.
  - For Python we produce JUnit XML files (small XML documents) named like `reports/<service>-unit.xml` or `reports/<service>-integration.xml`.
  - Python jobs also produce coverage outputs named like `reports/<service>-coverage.xml` and `reports/<service>-htmlcov/`.
  - For the frontend we run Node's test runner directly with the built-in JUnit reporter, which writes `reports/frontend-tests.xml` without an intermediate JSON conversion step.

- Where CI stores those reports:
  - After a job finishes, the workflow uploads those XML files as "artifacts" attached to the workflow run. You can download them later.
  - Coverage artifacts are uploaded separately as `python-unit-coverage-<service>` and `python-integration-coverage-<service>`.

- How to find the reports in GitHub (step-by-step):
  1. Open the repository in GitHub and click the **Actions** tab.
 2. Pick the workflow you want (for example "Microservices Unit Tests" or "Integration Tests").
 3. Select a specific run from the list (the runs are ordered by time, newest first).
 4. On the right-hand side of the run page you will see an **Artifacts** section. Click the artifact name (for example `python-unit-reports-ai-service` or `python-unit-coverage-ai-service`) to download the report files.
 5. Also check the **Tests** tab (if present) on the run page — the test reporter action we added will show a friendly summary of test suites and failures there.
 6. Open the downloaded HTML coverage folder locally and open the `index.html` file to inspect file-by-file coverage.

- Common troubleshooting actions (what to do when a test fails):
  - Click the failing job in the workflow run to view the step logs — logs show stack traces and the exact failing assertion.
  - Download the JUnit XML artifact and open it with a text editor to see which test name failed and any failure messages. You can also upload the XML to test-report viewers if needed.
  - If the failure is in the frontend tests, download `frontend-tests.xml` (from the artifact `frontend-test-report`) — it contains the direct JUnit results from Node's built-in reporter.

- Quick local commands that mirror CI (copy/paste):
  - Full 7-service pass (Windows PowerShell example):

```powershell
# create venv if missing, then activate and run full pass
if (-Not (Test-Path .\.venv\Scripts\Activate.ps1)) { python -m venv .venv }
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python microservices/scripts/full_test_pass.py
```

  - Python unit test (writes JUnit XML):

```bash
pytest microservices/conversations-service/tests/test_health.py --junitxml=reports/conversations-unit.xml
```

  - Python integration test (writes JUnit XML):

```bash
pytest microservices/conversations-service/tests/test_api.py --junitxml=reports/conversations-integration.xml
```

  - Frontend tests (JUnit XML):

```bash
cd microservices/frontend
npm run test:reports
```

- Naming conventions used by our workflows (so you can quickly locate the right artifact):
  - `python-unit-reports-<service>` — uploaded artifact for each Python service's fast unit/health tests.
  - `python-unit-coverage-<service>` — uploaded coverage artifact for each Python service's fast unit/health tests.
  - `frontend-test-report` — uploaded artifact that contains the frontend JUnit XML.
  - `python-integration-reports-<service>` — uploaded artifact for integration/API tests run on `main`.
  - `python-integration-coverage-<service>` — uploaded coverage artifact for integration/API tests run on `main`.
  - `microservices/scripts/full_test_pass.py` — helper for the exact six-service local rerun.

If you'd like, I can add a short screenshot guide (image) showing where to click in the Actions UI, or add a tiny script that automatically downloads the latest test artifact for a workflow run.
If you want, I can:
- Mark each existing test as `unit` or `integration` and adjust the workflow to run only units on PRs.
- Add JUnit-style test reporting to the workflow.
- Add a separate `integration-tests.yml` workflow that runs slower integration tests on `main`.

Tell me which option you prefer and I will implement it.
