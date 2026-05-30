want to run them locally and share the output# CI Screenshot Guide — how to capture test reports from GitHub Actions

This guide shows exactly what screenshots to take when you want to capture CI test results and artifacts from GitHub Actions. Use these screenshots for documentation, PR comments, or to attach to bug reports.

Suggested filenames (use these when saving screenshots):
- `actions-workflow-list.png` — shows the list of workflows in the **Actions** tab
- `actions-run-summary.png` — shows the selected run's summary (top of the run page)
- `actions-job-logs.png` — shows the expanded job logs for the failing job (click the job, expand failing step)
- `actions-tests-tab.png` — shows the Tests tab (if present) with failures highlighted
- `actions-artifacts.png` — shows the Artifacts section on the run page

Where to capture (step-by-step)
1. Open the repository on GitHub and click **Actions**. Capture the full page and save as `actions-workflow-list.png`.
   - Crop to show the left workflows list and the runs list on the right.

2. Click the workflow you want (for example "Microservices Unit Tests") and open the most recent run. Capture the top area of the run summary (status, duration, branch) and save as `actions-run-summary.png`.
   - Include the run header and the list of jobs visible below it.

3. Click the failing job (red) or the job you want to inspect. Expand the step that contains the failure and capture `actions-job-logs.png`.
   - Make sure the captured logs show the failing assertion or stack trace.

4. If the workflow run shows a **Tests** tab, open it and capture `actions-tests-tab.png`.
   - The `dorny/test-reporter` action surfaces a summary there; capture the failure rows.

5. On the run page, find the **Artifacts** box (normally on the right side). Click the artifact name (e.g., `python-unit-reports-ai-service`) so the download button is visible and capture `actions-artifacts.png`.

6. (Optional) Download the JUnit XML artifact, open it in a text editor, and capture a snippet of the failing `<testcase>` element. Name it `artifact-xml-snippet.png`.

Tips for clear screenshots
- Use your browser's zoom so text is readable (100–125% works well).
- Expand the specific job/step so the failing lines are visible in a single screenshot.
- If you need to redact secrets or tokens, blur or crop them before sharing.

If you want, I can add a small PowerShell script that uses the GitHub CLI to download the latest artifact automatically — would you like that?

Sample annotated images

Below are simple sample images you can use as reference when taking screenshots. They are stored in `infra/images/` in the repository.

![Workflows list](infra/images/actions-workflow-list.svg)

![Run summary](infra/images/actions-run-summary.svg)

![Job logs example](infra/images/actions-job-logs.svg)

![Tests tab example](infra/images/actions-tests-tab.svg)

![Artifacts panel example](infra/images/actions-artifacts.svg)
