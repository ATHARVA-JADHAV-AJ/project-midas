# Project Midas â€” LangGraph State Machine
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Defines the Project Midas agent graph using LangGraph's StateGraph.

Topology:
  [START]
    â””â”€â”€ classify_intent
          â”œâ”€â”€ (vision)   â†’ vision_extract  â†’ reason_and_code
          â”œâ”€â”€ (math)     â†’ reason_and_code
          â””â”€â”€ (document) â†’ rag_retrieve    â†’ reason_and_code
                               â†“
                         execute_code
                               â”œâ”€â”€ success    â†’ ground_check â†’ format_output â†’ [END]
                               â”œâ”€â”€ syntax/timeout (iteration < 3) â†’ reason_and_code
                               â””â”€â”€ other / max_iterations â†’ fail_node â†’ [END]

All state transitions are deterministic. No LLM output can select a graph edge.
"""

from datetime import datetime, timezone
from core.audit import log_audit_event
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from core.state import MidasState
from core.nodes.classifier import classify_intent
from core.nodes.rag_retriever import retrieve_context
from core.nodes.reasoner import reason_and_code, vision_extract, draft_from_extraction_node
from core.nodes.code_executor import execute_code
from core.nodes.ground_check import check_groundedness
from core.nodes.output_formatter import format_output
import logging

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


from core.nodes.standard_chat import standard_chat

# ... later in the file ...

def route_by_intent(state: MidasState) -> str:
    """Route after classification based on resolved intent."""
    intent = state.get("intent", "document")
    if intent == "vision":
        return "vision_extract"
    elif intent == "math":
        # Math tasks go straight to the reasoner â€” no RAG needed for pure computation
        return "reason_and_code"
    elif intent == "chat":
        return "standard_chat"
    else:
        return "rag_retrieve"

def should_retry(state: MidasState) -> str:
    """
    Decides what happens after code execution:
      - No error â†’ proceed to groundedness check
      - SyntaxError or TimeoutError, iteration < MAX_ITERATIONS â†’ loop back to reasoner
      - Any other error, or max iterations reached â†’ fail
    """
    error_type = state.get("error_type")
    iteration = state.get("iteration", 0)

    if error_type is None:
        # Clean execution â€” advance
        return "ground_check"

    if error_type in ("syntax", "timeout", "runtime", "file_type_mismatch") and iteration < MAX_ITERATIONS:
        logger.info(f"[{state['task_id']}] Retrying after {error_type} error (iteration {iteration}/{MAX_ITERATIONS})")
        return "reason_and_code"

    # RuntimeError or exhausted retries
    return "fail_node"


# â”€â”€ Fail node â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def fail_node(state: MidasState) -> MidasState:
    """Terminal failure node. Logs and packages the error for delivery."""
    error_type = state.get("error_type", "unknown")
    file_type = state.get("file_type", "unknown")
    raw_error = state.get("error", "Unknown error")
    iterations = state.get("iteration", 0)
    
    logger.error(f"[{state['task_id']}] Task failed after {iterations} iterations. Error type: {error_type}. Error: {raw_error}")
    
    # Build a type-specific, honest error message
    if error_type == "file_type_mismatch":
        type_names = {"pdf": "PDF document", "docx": "Word document", "txt": "text file", "image": "image"}
        type_name = type_names.get(file_type, file_type)
        user_message = (
            f"The uploaded file appears to be a {type_name}, not a spreadsheet. "
            f"We attempted to analyze it as a document instead, but could not extract "
            f"meaningful results after {iterations} attempts. "
            f"If this file contains tabular data, try converting it to .xlsx or .csv format."
        )
    elif error_type == "syntax":
        user_message = (
            f"The system generated code with syntax errors that could not be resolved "
            f"after {iterations} attempts. This is an internal issue, not something "
            f"rephrasing would fix. Technical detail: {raw_error[:200]}"
        )
    elif error_type == "timeout":
        user_message = (
            f"The computation timed out after {iterations} attempts. "
            f"The task may be too complex for the current system. "
            f"Try breaking it into smaller steps."
        )
    elif error_type == "runtime":
        user_message = (
            f"The code execution failed after {iterations} attempts. "
            f"Technical detail: {raw_error[:200]}"
        )
    else:
        user_message = f"The task could not be completed. Technical detail: {raw_error[:200]}"

    duration_ms = int((datetime.now(timezone.utc).timestamp() - state.get('_start_time', datetime.now(timezone.utc).timestamp())) * 1000)
    log_audit_event({
        "task_id": state["task_id"],
        "user_id_hash": state.get("user_id_hash", ""),
        "intent": state.get("intent", "unknown"),
        "result_type": "failed",
        "output_path": None,
        "ground_score": state.get("ground_score"),
        "is_grounded": state.get("is_grounded"),
        "iterations": iterations,
        "duration_ms": duration_ms,
        "error": raw_error,
        "tier_b_dispatched": False,
    })
    return {
        **state,
        "execution_result": user_message,
        "final_output_path": None,
    }


def route_after_vision(state: MidasState) -> str:
    if state.get("chain_to") == "draft_from_extraction":
        return "draft_from_extraction"
    return "format_output"

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "checkpoints.sqlite")
conn = sqlite3.connect(db_path, check_same_thread=False)
global_checkpointer = SqliteSaver(conn)
# â”€â”€ Graph assembly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_graph() -> StateGraph:
    graph = StateGraph(MidasState)

    # Register nodes
    from core.nodes.render_flowchart import render_flowchart
    from core.nodes.answer_polisher import polish_answer
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("rag_retrieve", retrieve_context)
    graph.add_node("vision_extract", vision_extract)  # Defined in reasoner.py
    graph.add_node("draft_from_extraction", draft_from_extraction_node)
    graph.add_node("reason_and_code", reason_and_code)
    graph.add_node("render_flowchart", render_flowchart)
    graph.add_node("execute_code", execute_code)
    graph.add_node("ground_check", check_groundedness)
    graph.add_node("polish_answer", polish_answer)
    graph.add_node("format_output", format_output)
    graph.add_node("fail_node", fail_node)
    graph.add_node("standard_chat", standard_chat)

    # Entry
    graph.set_entry_point("classify_intent")

    # Intent routing
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "vision_extract": "vision_extract",
            "reason_and_code": "reason_and_code",
            "rag_retrieve": "rag_retrieve",
            "standard_chat": "standard_chat",
        },
    )

    # RAG â†’ reasoner
    graph.add_edge("rag_retrieve", "reason_and_code")
    
    # Vision extract â†’ draft or format
    graph.add_conditional_edges(
        "vision_extract",
        route_after_vision,
        {
            "draft_from_extraction": "draft_from_extraction",
            "format_output": "format_output"
        }
    )
    graph.add_edge("draft_from_extraction", "ground_check")

    def route_after_reasoner(state: MidasState) -> str:
        if "flowchart" in state["prompt"].lower():
            return "render_flowchart"
        return "execute_code"

    # Reasoner → executor or flowchart renderer
    graph.add_conditional_edges(
        "reason_and_code",
        route_after_reasoner,
        {
            "execute_code": "execute_code",
            "render_flowchart": "render_flowchart",
        }
    )
    
    # Flowchart rendering goes straight to output formatting
    graph.add_edge("render_flowchart", "format_output")

    # Standard chat bypasses RAG and sandbox, goes straight to output formatting
    graph.add_edge("standard_chat", "format_output")

    # Execution routing â€” the only branching point after the reasoner
    graph.add_conditional_edges(
        "execute_code",
        should_retry,
        {
            "ground_check": "ground_check",
            "reason_and_code": "reason_and_code",
            "fail_node": "fail_node",
        },
    )

    # Success path: ground_check → polish_answer → format_output
    graph.add_edge("ground_check", "polish_answer")
    graph.add_edge("polish_answer", "format_output")
    graph.add_edge("format_output", END)
    graph.add_edge("fail_node", END)

    return graph.compile(checkpointer=global_checkpointer)


# Module-level compiled graph â€” imported by queue/tasks.py
MIDAS_GRAPH = build_graph()

