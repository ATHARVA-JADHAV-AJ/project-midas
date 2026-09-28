import os
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
import schemdraw
import schemdraw.flow as flow

from core.state import MidasState
from api.stream import publish

logger = logging.getLogger(__name__)
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", "/app/outputs"))

class FlowchartStep(BaseModel):
    id: str
    label: str
    type: Literal["step", "decision"]
    next: list[str] = []

class FlowchartSpec(BaseModel):
    title: str
    steps: list[FlowchartStep]

def render_flowchart_image(spec: FlowchartSpec, output_path: str) -> str:
    """Renders a validated FlowchartSpec to a PNG image using schemdraw."""
    with schemdraw.Drawing(file=output_path, show=False) as d:
        node_map = {}
        for step in spec.steps:
            shape = flow.Decision if step.type == "decision" else flow.Box
            node_map[step.id] = d.add(shape(label=step.label))
        
        for step in spec.steps:
            for next_id in step.next:
                if step.id in node_map and next_id in node_map:
                    d.add(flow.Arrow().at(node_map[step.id].S).to(node_map[next_id].N))
    return output_path

def render_flowchart(state: MidasState) -> MidasState:
    """
    Node: render_flowchart
    Takes the structured JSON output from the reasoner, validates it via Pydantic,
    and draws the flowchart. If parsing fails, returns plain text.
    """
    task_id = state["task_id"]
    content = state.get("execution_result", "")
    
    publish(task_id, "thought", "Parsing and rendering flowchart...")
    
    try:
        import re
        match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = match.group(1).strip()
        else:
            json_str = content.strip()
            
        data = json.loads(json_str)
        spec = FlowchartSpec(**data)
        
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        file_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"flowchart_{timestamp}_{file_id}.svg"
        output_path = OUTPUTS_DIR / filename
        
        render_flowchart_image(spec, str(output_path))
        
        logger.info(f"[{task_id}] Rendered flowchart to {output_path}")
        publish(task_id, "thought", "Flowchart rendered successfully.")
        
        return {**state, "execution_result": f"Flowchart generated: {filename}", "flowchart_path": str(output_path)}
        
    except Exception as e:
        logger.warning(f"[{task_id}] Flowchart rendering failed: {e}. Falling back to plain text.")
        publish(task_id, "thought", f"Failed to render flowchart ({e}), falling back to text.")
        return state
