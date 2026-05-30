import importlib.util
from pathlib import Path


def load_module():
    service_root = Path(__file__).resolve().parent.parent
    module_path = service_root / "main.py"
    spec = importlib.util.spec_from_file_location("ai_service_main", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_health_endpoint_payload():
    module = load_module()
    payload = module.health()

    assert payload["status"] == "ok"
    assert payload["service"] == "ai-worker"
