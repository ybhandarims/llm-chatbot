import warnings

# Suppress Starlette's deprecation about httpx/TestClient until dependencies are upgraded.
warnings.filterwarnings(
    "ignore",
    "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead."
)
