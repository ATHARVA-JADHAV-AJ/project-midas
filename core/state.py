# Project Midas — shared LangGraph state TypedDict
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
from typing import TypedDict, Optional, Literal, List

class MidasState(TypedDict):
    task_id: str
    conversation_id: str
    messages: List[dict]        # Chat history: [{"role": "user"|"assistant", "content": "..."}]
    prompt: str
    user_id_hash: str          # SHA-256 of user ID — passed through for audit logging
    intent: Optional[Literal["vision", "math", "document", "chat"]]
    file_path: Optional[str]   # Absolute path to the uploaded file (None if no file)
    file_type: Optional[str]   # Verified file type from magic bytes: "pdf", "xlsx", "csv", "docx", "image", "txt", "unknown"
    context: List[str]          # RAG context chunks retrieved from Qdrant
    generated_code: str         # Most recent code produced by the reasoner
    timed_out_code: str         # Code from the iteration that caused a TimeoutError (for retry prompt)
    execution_result: str
    error: Optional[str]        # Raw error string from executor (SyntaxError, TimeoutError, etc.)
    error_type: Optional[Literal["syntax", "timeout", "runtime", "file_type_mismatch", None]]
    iteration: int              # Current retry count — hard capped at max_iterations=3 in graph.py
    ground_score: Optional[float]  # Cosine similarity score from groundedness check
    is_grounded: Optional[bool]    # True if score >= GROUND_CHECK_THRESHOLD
    final_output_path: Optional[str]
    chain_to: Optional[str]
    extraction_result: Optional[dict]
    plan: List[dict]           # Agent plan: [{"step_id": int, "type": str, "description": str, "status": str}]
    current_step: int          # Current step index in the plan (0-based)
    step_results: List[dict]   # Accumulated outputs from completed steps
