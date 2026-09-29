# Project Midas — LangGraph State Machine (v7.0 Agentic Loop)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Defines the Project Midas v7.0 agent graph using LangGraph's StateGraph.

v7.0 Topology — True Agentic Loop (Plan → Act → Observe → Iterate):

  [START]
    └── classify_intent
          ├── (chat)     → standard_chat → format_output → [END]
          └── (vision/math/document) → agent_planner → agent_step_router
                                          ↕ (loop)
              ┌─ rag_search      → rag_retrieve → agent_observer
              ├─ code_execute    → reason_and_code → execute_code → agent_observer
              ├─ vision_extract  → vision_extract → agent_observer
              └─ generate_doc    → draft_from_extraction → agent_observer
                                                              ↓
                                      ├── next_step → agent_step_router (loop back)
                                      ├── done      → ground_check → polish → format → [END]
                                      └── failed    → fail_node → [END]

MAX_AGENT_STEPS = 5  (hard cap to prevent infinite loops)
MAX_ITERATIONS  = 3  (code retry cap per step)
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
from core.nodes.standard_chat import standard_chat
from core.nodes.answer_polisher import polish_answer
from core.nodes.agent_planner import agent_planner
from core.nodes.agent_observer import agent_observer, route_after_observer, route_agent_step
import logging

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


# ── Routing Functions ────────────────────────────────────────────────

def route_by_intent(state: MidasState) -> str:
    """Route after classification. Chat bypasses the agentic loop."""
    intent = state.get("intent", "document")
    if intent == "chat":
        return "standard_chat"
    # All other intents (vision, math, document) go through the agentic planner
    return "agent_planner"


def should_retry(state: MidasState) -> str:
    """
    Decides what happens after code execution within a step:
      - No error → proceed to observer (step complete)
      - Retryable error, iteration < MAX → loop back to reasoner
      - Max iterations or fatal error → route to observer with error state
    """
    error_type = state.get("error_type")
    iteration = state.get("iteration", 0)

    if error_type is None:
        # Clean execution — advance to observer
        return "agent_observer"

    if error_type in ("syntax", "timeout", "runtime", "file_type_mismatch") and iteration < MAX_ITERATIONS:
        logger.info(f"[{state['task_id']}] Retrying after {error_type} error (iteration {iteration}/{MAX_ITERATIONS})")
        return "reason_and_code"

    # Exhausted retries — still route to observer (it will decide to fail or continue)
    return "agent_observer"


def route_after_vision(state: MidasState) -> str:
    """After vision extraction, always route to observer (agentic loop)."""
    return "agent_observer"


# ── Agent Step Router ────────────────────────────────────────────────

def agent_step_router_fn(state: MidasState) -> str:
    """Routes to the correct action node based on the current plan step type."""
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)

    if current_step >= len(plan):
        return "ground_check"

    step_type = plan[current_step].get("type", "code_execute")

    type_map = {
        "rag_search": "rag_retrieve",
        "code_execute": "reason_and_code",
        "vision_extract": "vision_extract",
        "generate_document": "draft_from_extraction",
    }

    return type_map.get(step_type, "reason_and_code")


def observer_route_fn(state: MidasState) -> str:
    """Routes after the observer evaluates a completed step."""
    result = route_after_observer(state)
    if result == "next_step":
        return "agent_step_router"
    elif result == "done":
        return "ground_check"
    else:
        return "fail_node"


# ── Fail node ────────────────────────────────────────────────────────

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


# ── Checkpointer ─────────────────────────────────────────────────────

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "checkpoints.sqlite")
conn = sqlite3.connect(db_path, check_same_thread=False)
global_checkpointer = SqliteSaver(conn)


# ── Graph assembly ────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(MidasState)

    # Register nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("standard_chat", standard_chat)
    graph.add_node("agent_planner", agent_planner)
    graph.add_node("rag_retrieve", retrieve_context)
    graph.add_node("vision_extract", vision_extract)
    graph.add_node("draft_from_extraction", draft_from_extraction_node)
    graph.add_node("reason_and_code", reason_and_code)
    graph.add_node("execute_code", execute_code)
    graph.add_node("agent_observer", agent_observer)
    graph.add_node("ground_check", check_groundedness)
    graph.add_node("polish_answer", polish_answer)
    graph.add_node("format_output", format_output)
    graph.add_node("fail_node", fail_node)

    # Entry
    graph.set_entry_point("classify_intent")

    # ── Intent routing ─────────────────────────────────────────────
    # Chat → direct response; everything else → agentic planner
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "standard_chat": "standard_chat",
            "agent_planner": "agent_planner",
        },
    )

    # Chat bypasses the agentic loop entirely
    graph.add_edge("standard_chat", "format_output")

    # ── Agentic Loop ───────────────────────────────────────────────
    # Planner → step router (first step)
    graph.add_conditional_edges(
        "agent_planner",
        agent_step_router_fn,
        {
            "rag_retrieve": "rag_retrieve",
            "reason_and_code": "reason_and_code",
            "vision_extract": "vision_extract",
            "draft_from_extraction": "draft_from_extraction",
            "ground_check": "ground_check",
        },
    )

    # Action nodes → observer (or retry loop for code execution)
    graph.add_edge("rag_retrieve", "agent_observer")

    graph.add_edge("reason_and_code", "execute_code")

    graph.add_conditional_edges(
        "execute_code",
        should_retry,
        {
            "agent_observer": "agent_observer",
            "reason_and_code": "reason_and_code",
        },
    )

    graph.add_conditional_edges(
        "vision_extract",
        route_after_vision,
        {
            "agent_observer": "agent_observer",
        },
    )

    graph.add_edge("draft_from_extraction", "agent_observer")

    # Observer → next step (loop), finalize, or fail
    # We use a virtual "agent_step_router" node that re-evaluates and routes
    graph.add_conditional_edges(
        "agent_observer",
        observer_route_fn,
        {
            "agent_step_router": "agent_planner",  # Re-enter planner to read next step
            "ground_check": "ground_check",
            "fail_node": "fail_node",
        },
    )

    # Note: We route "next_step" back to agent_planner, but since the plan is
    # already created, agent_planner will detect an existing plan and act as a
    # pass-through step router. We'll handle this by adding a lightweight
    # "step_dispatch" node that simply reads the current step and routes.

    # ── Success path ───────────────────────────────────────────────
    graph.add_edge("ground_check", "polish_answer")
    graph.add_edge("polish_answer", "format_output")
    graph.add_edge("format_output", END)
    graph.add_edge("fail_node", END)

    return graph.compile(checkpointer=global_checkpointer)


# Module-level compiled graph — imported by task_queue/tasks.py
MIDAS_GRAPH = build_graph()
