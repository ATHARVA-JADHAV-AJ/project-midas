# Project Midas — Agent Observer Node (v7.0 Agentic Loop)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Evaluates the result of the most recently completed step.
Decides whether to:
  - Advance to the next planned step ("next_step")
  - Finalize the output ("done")
  - Mark the task as failed ("failed")

This is the "Observe" phase of the Plan → Act → Observe → Iterate loop.
"""

import os
import logging
import asyncio
import ollama

from core.state import MidasState
from api.stream import publish
from models.vram_manager import ensure_model_loaded
from models.registry import get_model_name

logger = logging.getLogger(__name__)

MODEL = get_model_name("reasoning", "qwen2.5:3b-instruct")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

MAX_AGENT_STEPS = 3


def agent_observer(state: MidasState) -> MidasState:
    """
    Node: agent_observer
    Evaluates the result of the last completed step and decides next action.
    """
    task_id = state["task_id"]
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    step_results = state.get("step_results", [])
    error = state.get("error")
    error_type = state.get("error_type")
    execution_result = state.get("execution_result", "")
    
    logger.info(f"[{task_id}] Observer evaluating step {current_step + 1}/{len(plan)}")
    
    # Record the result of the just-completed step
    if current_step < len(plan):
        completed_step = plan[current_step].copy()
        completed_step["status"] = "failed" if error_type else "done"
        completed_step["result"] = execution_result[:2000] if execution_result else ""
        if error:
            completed_step["error"] = str(error)[:500]
        
        # Update step_results
        step_results = list(step_results)  # copy
        step_results.append(completed_step)
        
        # Update plan status
        plan = list(plan)  # copy
        if current_step < len(plan):
            plan[current_step] = {**plan[current_step], "status": completed_step["status"]}
    
    # Check if there's a critical failure that should stop execution
    if error_type and error_type not in ("syntax", "runtime"):
        # Timeout or file_type_mismatch — don't continue
        publish(task_id, "thought", f"Step {current_step + 1} failed critically. Finalizing...")
        return {
            **state,
            "plan": plan,
            "step_results": step_results,
            "current_step": len(plan),  # Force done
        }
    
    # Advance to next step
    next_step = current_step + 1
    
    # Check if we've completed all planned steps
    if next_step >= len(plan):
        publish(task_id, "thought", f"All {len(plan)} steps complete. Generating final output...")
        
        # Merge all step results into a single execution_result for downstream formatting
        merged_results = []
        for sr in step_results:
            if sr.get("result"):
                merged_results.append(f"## Step {sr['step_id']}: {sr.get('description', '')}\n{sr['result']}")
        
        final_result = "\n\n".join(merged_results) if merged_results else execution_result
        
        return {
            **state,
            "plan": plan,
            "step_results": step_results,
            "current_step": next_step,
            "execution_result": final_result,
            "error": None,
            "error_type": None,
        }
    
    # More steps to go — prepare for next step
    next_plan_step = plan[next_step]
    publish(task_id, "thought", f"Step {next_step + 1}/{len(plan)}: {next_plan_step['description']}")
    logger.info(f"[{task_id}] Observer advancing to step {next_step + 1}: {next_plan_step['type']}")
    
    # Clear error state for the next step
    return {
        **state,
        "plan": plan,
        "step_results": step_results,
        "current_step": next_step,
        "error": None,
        "error_type": None,
        "iteration": 0,  # Reset retry counter for new step
    }


def route_after_observer(state: MidasState) -> str:
    """
    Conditional edge: decides where to route after observation.
    Returns: 'next_step' | 'done' | 'failed'
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    
    # All steps complete or forced done
    if current_step >= len(plan):
        # Check if we have any successful results
        step_results = state.get("step_results", [])
        has_results = any(sr.get("status") == "done" for sr in step_results)
        if has_results or state.get("execution_result"):
            return "done"
        return "failed"
    
    return "next_step"


def route_agent_step(state: MidasState) -> str:
    """
    Conditional edge: routes to the correct action node based on the current step type.
    Returns: 'rag_search' | 'code_execute' | 'vision_extract' | 'generate_document'
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    
    if current_step >= len(plan):
        return "done"
    
    step_type = plan[current_step].get("type", "code_execute")
    
    type_map = {
        "rag_search": "rag_search",
        "code_execute": "code_execute",
        "vision_extract": "vision_extract",
        "generate_document": "generate_document",
    }
    
    return type_map.get(step_type, "code_execute")
