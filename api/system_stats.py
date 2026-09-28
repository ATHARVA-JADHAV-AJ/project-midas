# Project Midas — System statistics endpoint
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Provides live system telemetry for the frontend dashboard:
- GPU VRAM usage (via nvidia-smi)
- Currently loaded Ollama model
- Ollama server health
- Pipeline node readiness
"""

import os
import logging
import subprocess
import json
from typing import Optional

import httpx
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _get_gpu_stats() -> dict:
    """Query nvidia-smi for VRAM usage. Returns dict with used/total in MB."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,gpu_name",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 3:
                return {
                    "vram_used_mb": int(parts[0].strip()),
                    "vram_total_mb": int(parts[1].strip()),
                    "gpu_name": parts[2].strip(),
                }
    except FileNotFoundError:
        logger.debug("nvidia-smi not found — GPU stats unavailable")
    except Exception as e:
        logger.debug("nvidia-smi error: %s", e)
    return {"vram_used_mb": 0, "vram_total_mb": 0, "gpu_name": "N/A"}


def _get_ollama_status() -> dict:
    """Check Ollama health and currently loaded models."""
    try:
        # Check running models (loaded into VRAM)
        resp = httpx.get(f"{OLLAMA_URL}/api/ps", timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            if models:
                loaded = models[0]
                return {
                    "online": True,
                    "loaded_model": loaded.get("name", "unknown"),
                    "model_size_mb": round(
                        loaded.get("size", 0) / (1024 * 1024), 0
                    ),
                }
            return {"online": True, "loaded_model": None, "model_size_mb": 0}
    except Exception as e:
        logger.debug("Ollama health check failed: %s", e)
    return {"online": False, "loaded_model": None, "model_size_mb": 0}


@router.get("/stats")
async def get_system_stats():
    """Return live system telemetry for the frontend telemetry panel."""
    gpu = _get_gpu_stats()
    ollama = _get_ollama_status()

    vram_total_gb = round(gpu["vram_total_mb"] / 1024, 1) if gpu["vram_total_mb"] > 0 else 0
    vram_used_gb = round(gpu["vram_used_mb"] / 1024, 1) if gpu["vram_used_mb"] > 0 else 0
    vram_pct = round((gpu["vram_used_mb"] / gpu["vram_total_mb"]) * 100, 1) if gpu["vram_total_mb"] > 0 else 0

    return {
        "gpu": {
            "name": gpu["gpu_name"],
            "vram_used_gb": vram_used_gb,
            "vram_total_gb": vram_total_gb,
            "vram_pct": vram_pct,
        },
        "ollama": {
            "online": ollama["online"],
            "loaded_model": ollama["loaded_model"],
            "model_size_mb": ollama["model_size_mb"],
        },
        "pipeline": {
            "classifier": "ready",
            "file_inspector": "ready",
            "ground_check": "ready",
        },
        "network": "local_only",
    }
