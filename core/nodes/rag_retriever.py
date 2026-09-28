# Project Midas — RAG Retrieval Node
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Retrieves relevant document context from the local Qdrant vector store.
Embedding runs on CPU only (OLLAMA_NUM_GPU_LAYERS=0 for the embed model).
Returns the top-k most relevant chunks as a list of strings in state.context.
"""

import os
import logging
from core.state import MidasState
from memory.embedder import embed_text
from memory.vector_store import search_similar
from api.stream import publish

logger = logging.getLogger(__name__)

TOP_K = int(os.getenv("RAG_TOP_K", "5"))


def retrieve_context(state: MidasState) -> MidasState:
    """
    Node: rag_retrieve
    Embeds the user prompt and fetches top-k matching chunks from Qdrant.
    If retrieval fails, continues with empty context — the reasoner will
    generate without RAG grounding (which the ground_check node will flag).
    """
    task_id = state["task_id"]
    prompt = state["prompt"]

    logger.info(f"[{task_id}] Starting RAG retrieval (top_k={TOP_K})")
    publish(task_id, "thought", "Retrieving relevant context from knowledge base...")

    try:
        query_vector = embed_text(prompt)
        chunks = search_similar(query_vector, top_k=TOP_K)
        logger.info(f"[{task_id}] Retrieved {len(chunks)} context chunks")
        publish(task_id, "thought", f"Retrieved {len(chunks)} relevant chunks.")
    except Exception as e:
        logger.warning(f"[{task_id}] RAG retrieval failed: {e}. Continuing without context.")
        chunks = []

    return {**state, "context": chunks}
