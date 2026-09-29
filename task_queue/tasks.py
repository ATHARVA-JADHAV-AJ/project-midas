# Project Midas — Celery Task Definitions
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Celery task entry points dispatched by queue/consumer.py.

Phase 2: stub replaced with real LangGraph graph.invoke() call.
The graph handles all intent routing, RAG, execution, grounding,
and output formatting internally.
"""

import hashlib
import logging
from datetime import datetime, timezone

from task_queue.worker import celery_app
from task_queue.queue_manager import set_task_status, get_task_status
from core.graph import MIDAS_GRAPH
from core.state import MidasState

logger = logging.getLogger(__name__)


@celery_app.task(name="task_queue.tasks.run_agent_task", bind=True, max_retries=0)
def run_agent_task(self, task_id: str, prompt: str) -> str:
    """
    Entry point for all agent tasks. Invokes the LangGraph state machine.

    `bind=True` gives access to `self` for Celery task introspection.
    `max_retries=0` disables automatic Celery retries — the graph's own
    iteration logic (max 3) handles retries internally. Failed tasks surface
    their error message through Redis rather than being silently re-queued.
    """
    logger.info(f"[{task_id}] Task starting — invoking LangGraph pipeline")
    set_task_status(task_id, "running")

    # Pull metadata from Redis — includes user identity stored by enqueue()
    task_meta = get_task_status(task_id)
    role = task_meta.get("role", "default") if task_meta else "default"
    user_identity = task_meta.get("user", "unknown") if task_meta else "unknown"
    user_id_hash = hashlib.sha256(user_identity.encode()).hexdigest()
    
    # Retrieve conversation_id (defaults to task_id if not present for backwards compat)
    conversation_id = task_meta.get("conversation_id", task_id) if task_meta else task_id

    # Fetch conversation history
    import json
    from task_queue.queue_manager import _redis
    history = []
    history_json = _redis.get(f"midas:conv:{conversation_id}")
    if history_json:
        history = json.loads(history_json)
        
    # Clean the prompt of metadata tags before adding to history
    clean_prompt = prompt
    import re as _re
    _file_match = _re.search(r"\[File Attached: (.*?) \| type: (\w+)\]\n\n(.*)", prompt, _re.DOTALL)
    _file_path, _file_type = None, None
    if _file_match:
        _file_path = _file_match.group(1)
        _file_type = _file_match.group(2)
        clean_prompt = _file_match.group(3)
    elif prompt.startswith("[File Attached:"):
        # Fallback if no newline
        _file_match_simple = _re.search(r"\[File Attached: (.*?) \| type: (\w+)\]", prompt)
        if _file_match_simple:
            _file_path = _file_match_simple.group(1)
            _file_type = _file_match_simple.group(2)

    history.append({"role": "user", "content": clean_prompt})
    _redis.set(f"midas:conv:{conversation_id}", json.dumps(history), ex=86400) # 1 day TTL

    initial_state: MidasState = {
        "task_id": task_id,
        "conversation_id": conversation_id,
        "messages": history,
        "prompt": prompt,
        "user_id_hash": user_id_hash,
        "intent": None,
        "file_path": _file_path,
        "file_type": _file_type,
        "context": [],
        "generated_code": "",
        "timed_out_code": "",
        "execution_result": "",
        "error": None,
        "error_type": None,
        "iteration": 0,
        "ground_score": None,
        "is_grounded": None,
        "final_output_path": None,
        "chain_to": None,
        "extraction_result": None,
        "_start_time": datetime.now(timezone.utc).timestamp(),
    }

    try:
        config = {"configurable": {"thread_id": conversation_id}}
        final_state = MIDAS_GRAPH.invoke(initial_state, config=config)
        state_snapshot = MIDAS_GRAPH.get_state(config)
        
        if state_snapshot.next:
            # Paused at an interrupt_before node
            generated_code = final_state.get("generated_code", "")
            set_task_status(task_id, "waiting_approval", result=generated_code)
            logger.info(f"[{task_id}] Task paused for HITL approval")
            return "waiting_approval"

        output_path = final_state.get("final_output_path")
        execution_result = final_state.get("execution_result", "")
        
        # Append assistant response to history
        if execution_result:
             history.append({"role": "assistant", "content": execution_result})
             _redis.set(f"midas:conv:{conversation_id}", json.dumps(history), ex=86400)

        set_task_status(
            task_id,
            "done",
            result=execution_result,  # NO MORE TRUNCATION
            output_path=output_path or "",
        )
        logger.info(f"[{task_id}] Task complete. Output: {output_path}")
        return execution_result

    except Exception as exc:
        logger.error(f"[{task_id}] Graph execution failed: {exc}", exc_info=True)
        set_task_status(task_id, "failed", error=str(exc))
        raise  # Re-raise so Celery marks FAILURE in its own result backend


@celery_app.task(name="task_queue.tasks.resume_agent_task", bind=True, max_retries=0)
def resume_agent_task(self, task_id: str) -> str:
    """Resumes a paused agent task after HITL approval."""
    logger.info(f"[{task_id}] Resuming LangGraph pipeline after approval")
    set_task_status(task_id, "running")

    try:
        config = {"configurable": {"thread_id": task_id}}
        final_state = MIDAS_GRAPH.invoke(None, config=config)
        state_snapshot = MIDAS_GRAPH.get_state(config)

        if state_snapshot.next:
            # Paused again (shouldn't happen with 1 interrupt point, but defensive)
            return "waiting_approval"

        output_path = final_state.get("final_output_path")
        execution_result = final_state.get("execution_result", "")
        is_grounded = final_state.get("is_grounded", True)

        result_summary = execution_result[:500] if execution_result else ""

        set_task_status(
            task_id,
            "done",
            result=result_summary,
            output_path=output_path or "",
        )
        logger.info(f"[{task_id}] Task complete. Output: {output_path}")
        return result_summary

    except Exception as exc:
        logger.error(f"[{task_id}] Graph execution failed on resume: {exc}", exc_info=True)
        set_task_status(task_id, "failed", error=str(exc))
        raise
