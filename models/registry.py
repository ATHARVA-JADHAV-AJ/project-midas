import yaml
import os
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "models_registry.yaml"

def load_registry():
    if not REGISTRY_PATH.exists():
        return {}
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("models", {})

_registry = load_registry()

def get_model_name(role: str, default: str) -> str:
    if role in _registry:
        return _registry[role].get("name", default)
    return os.getenv(f"MODEL_{role.upper()}", default)
