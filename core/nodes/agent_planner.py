# Project Midas — Agent Planner Node (v7.0 Agentic Loop)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Analyzes the user's task and produces a structured multi-step plan.
For simple tasks, generates a single-step plan.
For complex tasks (multi-document analysis, report generation, etc.),
generates 2-5 steps that the agent will execute autonomously.
"""

import os
import json
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

PLANNER_PROMPT = """\
You are Midas Defense AI v7.0 Task Planner. Analyze the user's request and create
an execution plan as a JSON array of steps.

Available step types:
- "rag_search": Search the local knowledge base for relevant documents
- "code_execute": Write and run a Python script (pandas, openpyxl) for data processing
- "vision_extract": Extract data from an uploaded image/scan
- "generate_document": Draft a formal document (.docx, .pptx) based on accumulated results

Rules:
- Output ONLY a valid JSON array wrapped in ```json fences
- Each step: {{"step_id": <int>, "type": "<type>", "description": "<what to do>"}}
- Simple tasks need only 1 step
- For complex tasks, structure the plan in exactly three steps: (1) RAG/Vision Extract to gather data, (2) Python Math (code_execute) to process it, and (3) Document Generation to draft the final output.
- Maximum {max_steps} steps total.
- Order steps logically.

User request: {prompt}
File attached: {file_info}
Detected intent: {intent}

Execution plan:"""


def agent_planner(state: MidasState) -> MidasState:
    """
    Node: agent_planner
    Analyzes the task and produces a structured multi-step execution plan.
    If called again during the agentic loop (plan already exists), acts as
    a pass-through — the graph's conditional edges will read current_step
    and route to the correct action node.
    """
    task_id = state["task_id"]
    intent = state.get("intent", "document")
    file_type = state.get("file_type")
    file_path = state.get("file_path")
    
    # Pass-through: if plan already exists, don't re-plan (agentic loop re-entry)
    existing_plan = state.get("plan", [])
    if existing_plan and state.get("current_step", 0) > 0:
        logger.info(f"[{task_id}] Agent planner re-entered (step {state['current_step'] + 1}/{len(existing_plan)}). Passing through.")
        return state
    
    publish(task_id, "thought", "Planning execution strategy...")
    logger.info(f"[{task_id}] Agent planner invoked (intent={intent})")
    
    asyncio.run(ensure_model_loaded(MODEL, task_id))
    
    file_info = "None"
    if file_path and file_type:
        file_info = f"{file_type.upper()} file at {file_path}"
    
    prompt_text = PLANNER_PROMPT.format(
        prompt=state["prompt"],
        file_info=file_info,
        intent=intent,
        max_steps=MAX_AGENT_STEPS
    )
    
    try:
        client = ollama.Client(host=OLLAMA_URL)
        response = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt_text}],
            options={"temperature": 0.1, "num_predict": 512},
        )
        raw = response["message"]["content"]
        
        # Extract JSON from markdown fences
        import re
        json_match = re.search(r'```(?:json)?\s*\n?(\[.*?\])\s*```', raw, re.DOTALL)
        if json_match:
            plan = json.loads(json_match.group(1))
        else:
            # Try parsing raw as JSON
            plan = json.loads(raw.strip())
        
        # Validate and cap
        if not isinstance(plan, list):
            raise ValueError("Plan is not a list")
        plan = plan[:MAX_AGENT_STEPS]
        
        # Normalize step structure
        valid_types = {"rag_search", "code_execute", "vision_extract", "generate_document"}
        normalized = []
        for i, step in enumerate(plan):
            step_type = step.get("type", "code_execute")
            if step_type not in valid_types:
                step_type = "code_execute"
            normalized.append({
                "step_id": i + 1,
                "type": step_type,
                "description": step.get("description", f"Step {i+1}"),
                "status": "pending"
            })
        plan = normalized
        
    except Exception as e:
        logger.warning(f"[{task_id}] Planner failed to generate plan: {e}. Using single-step fallback.")
        # Fallback: single-step plan based on intent
        fallback_type = {
            "vision": "vision_extract",
            "math": "code_execute",
            "document": "rag_search",
        }.get(intent, "code_execute")
        plan = [{
            "step_id": 1,
            "type": fallback_type,
            "description": state["prompt"],
            "status": "pending"
        }]
    
    plan_summary = " → ".join([f"{s['step_id']}. {s['type']}" for s in plan])
    publish(task_id, "thought", f"Plan: {plan_summary}")
    logger.info(f"[{task_id}] Agent plan: {plan_summary}")
    
    return {
        **state,
        "plan": plan,
        "current_step": 0,
        "step_results": []
    }
