# Project Midas — Answer Polisher Node
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Post-processing node that takes the raw stdout from the sandbox
and reformats it into clean, human-readable markdown using a
second LLM pass. This is the "Gemini-style" formatting layer.

Uses llama3.2 (3B) for formatting — separate from the qwen2.5
reasoning model — so the formatting quality is independent of
the code-generation quality.
"""

import logging
import os
import ollama

from core.state import MidasState
from models.registry import get_model_name
from models.vram_manager import ensure_model_loaded
from api.stream import publish
import asyncio

logger = logging.getLogger(__name__)

# Use llama3.2 for natural language formatting (better prose than qwen)
MODEL = get_model_name("formatter", "llama3.2:latest")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

POLISHER_PROMPT = """\
You are a professional report formatter for MRPL (Mangalore Refinery and Petrochemicals Limited).

Your job: take the raw output below and reformat it into clean, well-structured, human-readable text.

Rules:
- Use markdown formatting: headers (##), bold (**), bullet points (-), tables (|), etc.
- For mathematical formulas, wrap them in $$ on their own line for LaTeX rendering
- Remove any Python artifacts, variable dumps, list representations, or debug output
- If the output contains numbers/statistics, present them in a clean table
- If the output is already clean text, just tidy the formatting slightly
- Keep ALL the actual data and numbers — do not invent or change any values
- Be concise and professional. No filler like "Here are the results"
- If the raw output is an error message, just say what went wrong in plain English

Raw output to format:
---
{raw_output}
---

Formatted output:"""


def polish_answer(state: MidasState) -> MidasState:
    """
    Node: polish_answer
    Takes raw execution_result and reformats it using a second LLM pass.
    Only runs if there is actual content to polish.
    """
    task_id = state["task_id"]
    raw = state.get("execution_result", "").strip()

    # Skip polishing if there's no content or if it's a chat response
    if not raw or state.get("intent") == "chat":
        return state

    # Skip polishing if the content is very short (< 30 chars) — already clean
    if len(raw) < 30:
        return state

    logger.info(f"[{task_id}] Polishing answer ({len(raw)} chars)")
    publish(task_id, "status", "Formatting answer...")

    try:
        asyncio.run(ensure_model_loaded(MODEL, task_id))

        client = ollama.Client(host=OLLAMA_URL)
        resp = client.chat(
            model=MODEL,
            messages=[
                {"role": "user", "content": POLISHER_PROMPT.format(raw_output=raw[:2000])}
            ],
            options={"temperature": 0.2, "num_predict": 1024},
        )

        polished = resp["message"]["content"].strip()

        if polished and len(polished) > 10:
            logger.info(f"[{task_id}] Answer polished successfully ({len(polished)} chars)")
            return {**state, "execution_result": polished}
        else:
            logger.warning(f"[{task_id}] Polisher returned empty/short response, keeping raw")
            return state

    except Exception as e:
        logger.warning(f"[{task_id}] Answer polishing failed ({e}), keeping raw output")
        return state
