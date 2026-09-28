"""
Project Midas — Pre-flight Health Check
Author: Atharva Kishor Jadhav (AJ)
---------------------------------------------------------------
Run before starting the stack to verify all required services are reachable.
Exits with code 0 if all checks pass, code 1 if any fail.

Usage:
    python scripts/health_check.py
"""

import sys
import os
import socket
import subprocess
from pathlib import Path

# Load .env manually without requiring python-dotenv to be installed yet
def load_env(path=".env"):
    if not Path(path).exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

load_env()

CHECKS = []
PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"


def check_tcp(name: str, host: str, port: int):
    """Verify a TCP port is open and accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"{PASS} {name} reachable at {host}:{port}")
            CHECKS.append(True)
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"{FAIL} {name} NOT reachable at {host}:{port} — {e}")
        CHECKS.append(False)


def check_ollama():
    """Verify Ollama is running and at least one model is available."""
    import urllib.request
    import json
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # When running on Windows host, host.docker.internal may not resolve.
    base = base.replace("host.docker.internal", "localhost")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=5) as r:
            data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            if models:
                print(f"{PASS} Ollama running. Models available: {', '.join(models)}")
            else:
                print(f"{WARN} Ollama running but no models pulled yet. Run: ollama pull qwen2.5:3b-instruct")
            CHECKS.append(True)
    except Exception as e:
        print(f"{FAIL} Ollama not reachable at {base} — {e}")
        CHECKS.append(False)


def check_env_secrets():
    """Warn if placeholder secrets haven't been replaced."""
    issues = []
    for key in ("JWT_SECRET", "DISPATCHER_SECRET"):
        val = os.getenv(key, "")
        if not val or "REPLACE_ME" in val:
            issues.append(key)
    if issues:
        print(f"{WARN} Placeholder secrets detected: {', '.join(issues)}. Run: python scripts/bootstrap.py")
    else:
        print(f"{PASS} JWT_SECRET and DISPATCHER_SECRET look configured.")


def check_users_json():
    users_file = os.getenv("USERS_FILE", "./users.json")
    if Path(users_file).exists():
        print(f"{PASS} users.json found at {users_file}")
    else:
        print(f"{FAIL} users.json not found. Run: python scripts/bootstrap.py")
        CHECKS.append(False)


if __name__ == "__main__":
    print("=" * 55)
    print("  Project Midas — Pre-flight Health Check")
    print("  Author: Atharva Kishor Jadhav (AJ)")
    print("=" * 55)

    # Parse service URLs from env
    redis_url  = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    check_tcp("Redis",  "localhost", 6379)
    check_tcp("Qdrant", "localhost", 6333)
    check_tcp("FastAPI API", "localhost", 8000)
    check_tcp("Tier B Dispatcher", "localhost", 8001)
    check_ollama()
    check_env_secrets()
    check_users_json()

    print("-" * 55)
    if all(CHECKS):
        print(f"{PASS} All checks passed. Stack is ready.")
        sys.exit(0)
    else:
        failed = CHECKS.count(False)
        print(f"{FAIL} {failed} check(s) failed. Resolve before starting.")
        sys.exit(1)
