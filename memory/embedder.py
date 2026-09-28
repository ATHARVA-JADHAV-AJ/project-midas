# Project Midas — Text Embedder (CPU-only)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Generates text embeddings using nomic-embed-text via the local Ollama server.

Forced CPU execution: the OLLAMA_EMBED_NUM_GPU_LAYERS env var is set to 0
in .env, ensuring the embedding model never competes with the reasoning or
vision model for VRAM. Embeddings run on system RAM.
"""

import os
import logging
from typing import List

try:
    import ollama
except ImportError:
    ollama = None

logger = logging.getLogger(__name__)

from models.registry import get_model_name
EMBED_MODEL = get_model_name("embedding", "nomic-embed-text")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# This option is passed with every embed call to pin the model to CPU.
# OLLAMA_MAX_LOADED_MODELS=1 is the env-level backstop; this is the
# per-call guarantee that the embed model uses zero GPU layers.
_CPU_OPTIONS = {"num_gpu_layers": 0}


def embed_text(text: str) -> List[float]:
    """
    Embed a single string using nomic-embed-text on CPU.
    Returns a list of floats (the embedding vector).
    Raises RuntimeError if the Ollama call fails.
    """
    if ollama is None:
        raise RuntimeError("ollama package not installed")

    client = ollama.Client(host=OLLAMA_URL)
    try:
        response = client.embeddings(
            model=EMBED_MODEL,
            prompt=text,
            options=_CPU_OPTIONS,
        )
        return response["embedding"]
    except Exception as e:
        logger.error(f"Embedding failed for text ({len(text)} chars): {e}")
        raise RuntimeError(f"Embedding failed: {e}") from e


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed a list of strings. Each call is sequential — Ollama embed is fast on CPU."""
    return [embed_text(t) for t in texts]
