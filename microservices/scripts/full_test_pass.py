from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)
NPM = which("npm.cmd") or which("npm") or "npm.cmd"


def run(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    backend_tests = [
        "microservices/ai-service/tests/test_health.py",
        "microservices/gateway/tests/test_health.py",
        "microservices/conversations-service/tests/test_health.py",
        "microservices/conversations-service/tests/test_api.py",
        "microservices/messages-service/tests/test_health.py",
        "microservices/settings-service/tests/test_health.py",
    ]

    run(
        [
            str(PYTHON),
            "-m",
            "pytest",
            "-W",
            "ignore::starlette.exceptions.StarletteDeprecationWarning",
            "--import-mode=importlib",
            *backend_tests,
            "-q",
        ],
        cwd=REPO_ROOT,
    )

    run([NPM, "test"], cwd=REPO_ROOT / "microservices" / "frontend")


if __name__ == "__main__":
    main()