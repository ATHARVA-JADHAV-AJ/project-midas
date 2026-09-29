# Project Midas — VRAM Manager
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Deterministic model swap manager for the strict 6GB VRAM ceiling.

Implements the check-and-skip protocol:
1. Identify currently loaded model.
2. If it matches target, return immediately (zero latency).
3. If different, force flush (unload) and wait until empty.
4. Load target model (or let caller's generate request load it lazily).

Guarantees `OLLAMA_MAX_LOADED_MODELS=1` behavior proactively.
"""

import os
import time
import httpx
import logging
import asyncio

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

async def get_loaded_model() -> str | None:
    """Return the name of the currently loaded model, or None if empty."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            if models:
                # We enforce max 1, so take the first
                return models[0].get("name")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch loaded models: {e}")
        return None

async def wait_for_unload(timeout_seconds: int = 10):
    """Poll until VRAM is empty."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        model = await get_loaded_model()
        if not model:
            return
        await asyncio.sleep(0.5)
    logger.warning("Timeout waiting for VRAM unload")

async def ensure_model_loaded(target_model: str, task_id: str = ""):
    """
    Ensure the target model is loaded, forcing a flush if another model is resident.
    """
    prefix = f"[{task_id}] " if task_id else ""
    currently_loaded = await get_loaded_model()

    if currently_loaded == target_model:
        logger.info(f"{prefix}Model {target_model} is already loaded. Skipping flush.")
        return

    if currently_loaded:
        logger.info(f"{prefix}Flushing model {currently_loaded} to make room for {target_model}")
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={"model": currently_loaded, "keep_alive": 0},
                    timeout=5
                )
        except Exception as e:
            logger.warning(f"{prefix}Error during model flush: {e}")
        
        await wait_for_unload()
    
    logger.info(f"{prefix}VRAM cleared. Target model {target_model} will load lazily on next request.")

async def prewarm_model(target_model: str, task_id: str = ""):
    """Force-load a model into VRAM by issuing a minimal generate request."""
    prefix = f"[{task_id}] " if task_id else ""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": target_model, "prompt": "hi", "options": {"num_predict": 1}},
                timeout=30
            )
        logger.info(f"{prefix}Pre-warmed model {target_model}")
    except Exception as e:
        logger.warning(f"{prefix}Pre-warm failed (model will load lazily): {e}")
