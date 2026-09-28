# Project Midas — Intent Classifier Node
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Classifies the user prompt into one of four intents:
  - vision    : task involves image analysis or visual data extraction
  - math      : task involves numerical computation, statistics, or data analysis
  - document  : task involves text generation, formatting, or document creation
  - chat      : general conversation

Now file-type-aware: the classifier receives the verified file type
(from magic bytes) as an explicit signal alongside the prompt text.
"""

import os
import logging
import re
from core.state import MidasState
from api.stream import publish
import asyncio
from models.vram_manager import ensure_model_loaded
from models.registry import get_model_name

try:
    import ollama
except ImportError:
    ollama = None

logger = logging.getLogger(__name__)

MODEL = get_model_name("reasoning", "qwen2.5:3b-instruct")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# The classifier prompt now includes file type context
CLASSIFIER_PROMPT = """\
You are a task router. Read the user request below and respond with EXACTLY one word:
  vision    — if the request involves processing an image, photograph, chart, or visual data
  math      — if the request involves numerical calculations, statistics, data tables, or financial figures on TABULAR data (Excel, CSV)
  document  — if the request involves reading, analyzing, summarizing, or searching a TEXT document (PDF, Word, TXT), or creating/formatting a document
  chat      — if the request is a simple conversational greeting, question, or general request not needing files

{file_context}
Respond with only the single word. No explanation.

User request: {prompt}"""


def classify_intent(state: MidasState) -> MidasState:
    """
    Node: classify_intent
    Reads state.prompt and state.file_type, writes state.intent.
    Falls back to 'chat' if the model response is ambiguous.
    """
    prompt = state["prompt"]
    task_id = state["task_id"]
    file_type = state.get("file_type")
    file_path = state.get("file_path", "")

    # Build file context string for the classifier
    if file_type and file_type != "unknown":
        from core.file_detector import get_file_type_description
        filename = os.path.basename(file_path) if file_path else "unknown"
        type_desc = get_file_type_description(file_type)
        file_context = (
            f"IMPORTANT: The user has attached a file: {filename} (verified type: {type_desc}).\n"
            f"Routing guidance based on file type:\n"
            f"  - If file is PDF/DOCX/TXT → prefer 'document' (unless user explicitly asks for calculations on tabular data)\n"
            f"  - If file is XLSX/CSV → prefer 'math' (tabular data analysis)\n"
            f"  - If file is an image → prefer 'vision'\n"
        )
    elif file_path:
        file_context = "The user has attached a file, but its type could not be determined.\n"
    else:
        file_context = "No file was attached.\n"

    logger.info(f"[{task_id}] Classifying intent for prompt: {prompt[:80]}... (file_type={file_type})")
    
    # Ensure correct model is loaded for VRAM ceiling
    asyncio.run(ensure_model_loaded(MODEL, task_id))

    try:
        client = ollama.Client(host=OLLAMA_URL)
        response = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": CLASSIFIER_PROMPT.format(
                prompt=prompt,
                file_context=file_context
            )}],
            options={"temperature": 0.0, "num_predict": 10},
        )
        raw = response["message"]["content"].strip().lower()
        # Extract the first word — model sometimes adds punctuation
        word = re.split(r"[^a-z]", raw)[0]
        intent = word
        if intent not in ("vision", "math", "document", "chat"):
            logger.warning(f"[{task_id}] Unrecognized intent '{intent}', defaulting to chat")
            intent = "chat"

        # Hard override: if file_type strongly disagrees with LLM intent, correct it
        if file_type == "image" and intent != "vision":
            logger.info(f"[{task_id}] File is an image but LLM said '{intent}' — overriding to vision")
            intent = "vision"
        elif file_type in ("pdf", "docx", "txt") and intent == "math":
            # PDF/DOCX are text documents — math intent would try pd.read_excel on them
            logger.info(f"[{task_id}] File is {file_type} but LLM said 'math' — overriding to document")
            intent = "document"

        logger.info(f"[{task_id}] Intent classified as: {intent}")
        publish(task_id, "status", f"Classified task intent: {intent}")
        return {**state, "intent": intent}

    except Exception as e:
        logger.error(f"[{task_id}] Classifier failed: {e}")
        # Default to document to let the reasoner attempt a generic fallback
        return {**state, "intent": "document"}

def determine_chain_intent(prompt: str) -> str | None:
    """Heuristic to decide if a vision task should chain into drafting."""
    prompt_lower = prompt.lower()
    chain_keywords = ["approval note", "report", "draft", "document", "word", "summary", "summarize"]
    for keyword in chain_keywords:
        if keyword in prompt_lower:
            return "draft_from_extraction"
    return None
