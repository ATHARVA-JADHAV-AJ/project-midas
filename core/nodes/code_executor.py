# Project Midas — Code Executor Node
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Executes agent-generated Python code in the RestrictedPython sandbox (Tier A).

Handles four failure categories with distinct retry behaviour:
  syntax             : SyntaxError in stderr → reasoner sees the error message
  timeout            : Code exceeded 30s wall time → reasoner sees the literal failing code
  runtime            : Any other non-zero exit → reasoner sees the traceback
  file_type_mismatch : Code tries to read a file with the wrong method (e.g. pd.read_excel on a PDF)
                       → detected BEFORE execution, rerouted through classify_intent
"""

import logging
import re
from core.state import MidasState
from sandbox.restricted_runner import run_restricted
from api.stream import publish

logger = logging.getLogger(__name__)

# Patterns that indicate reading a file as a spreadsheet
_EXCEL_READ_PATTERNS = re.compile(r"pd\.read_excel|load_workbook|openpyxl\.load_workbook", re.IGNORECASE)
_CSV_READ_PATTERNS = re.compile(r"pd\.read_csv", re.IGNORECASE)


def _check_file_type_mismatch(code: str, file_type: str | None, file_path: str | None) -> str | None:
    """
    Pre-execution safety net: check if the generated code's read method
    matches the actual file type. Returns an error message if there's a
    mismatch, or None if everything looks fine.
    """
    if not file_type or not file_path:
        return None  # No file attached, no mismatch possible

    if file_type in ("xlsx",):
        # xlsx file — pd.read_excel and load_workbook are fine
        return None

    if file_type in ("csv",):
        # csv file — pd.read_csv is fine, pd.read_excel is wrong
        if _EXCEL_READ_PATTERNS.search(code):
            return (
                f"Your code tries to read '{file_path}' with pd.read_excel() or load_workbook(), "
                f"but this file is a CSV, not an Excel file. Use pd.read_csv() instead."
            )
        return None

    if file_type in ("pdf", "docx", "txt"):
        # Text documents — neither pd.read_excel nor pd.read_csv will work
        if _EXCEL_READ_PATTERNS.search(code) or _CSV_READ_PATTERNS.search(code):
            type_name = {"pdf": "PDF document", "docx": "Word document", "txt": "text file"}.get(file_type, file_type)
            return (
                f"Your code tries to read '{file_path}' with pandas, but this file is a {type_name}, "
                f"not a spreadsheet. Pandas cannot read {file_type.upper()} files. "
                f"The file's text content has been extracted via the knowledge base and provided in the context."
            )
        return None

    if file_type == "image":
        if _EXCEL_READ_PATTERNS.search(code) or _CSV_READ_PATTERNS.search(code):
            return (
                f"Your code tries to read '{file_path}' with pandas, but this file is an image. "
                f"Image data has been extracted via vision AI and provided in the context."
            )
        return None

    return None  # Unknown file type — don't block


def execute_code(state: MidasState) -> MidasState:
    """
    Node: execute_code
    Runs state.generated_code through the RestrictedPython sandbox.
    Returns updated state with execution_result, error, error_type.
    """
    task_id = state["task_id"]
    code = state.get("generated_code", "")

    if not code.strip():
        return {
            **state,
            "error": "Reasoner produced empty code.",
            "error_type": "runtime",
        }

    # Pre-execution guard: check for file type mismatch BEFORE running the code
    file_type = state.get("file_type")
    file_path = state.get("file_path")
    mismatch_error = _check_file_type_mismatch(code, file_type, file_path)
    if mismatch_error:
        logger.warning(f"[{task_id}] File type mismatch detected: {mismatch_error}")
        publish(task_id, "error", f"File type mismatch: {mismatch_error[:200]}")
        return {
            **state,
            "execution_result": "",
            "error": mismatch_error,
            "error_type": "file_type_mismatch",
            "timed_out_code": "",
        }

    publish(task_id, "status", "Executing generated code in sandbox...")
    logger.info(f"[{task_id}] Executing code ({len(code)} chars) in Tier A sandbox")

    result = run_restricted(code, timeout_seconds=30)

    if result["timed_out"]:
        logger.warning(f"[{task_id}] Code timed out after 30s")
        publish(task_id, "error", "Execution timed out — retrying with bounded logic")
        return {
            **state,
            "execution_result": "",
            "error": "Execution timed out after 30 seconds.",
            "error_type": "timeout",
            "timed_out_code": code,  # Preserved verbatim for the retry prompt
        }

    if "SyntaxError" in result["stderr"]:
        logger.warning(f"[{task_id}] SyntaxError detected")
        publish(task_id, "error", f"SyntaxError: {result['stderr'][:200]}")
        return {
            **state,
            "execution_result": "",
            "error": result["stderr"],
            "error_type": "syntax",
            "timed_out_code": "",
        }

    if result["exit_code"] != 0:
        logger.error(f"[{task_id}] Runtime error (exit {result['exit_code']}): {result['stderr'][:300]}")
        publish(task_id, "error", f"Runtime error: {result['stderr'][:200]}")
        return {
            **state,
            "execution_result": result["stderr"],
            "error": result["stderr"],
            "error_type": "runtime",
            "timed_out_code": "",
        }

    # Clean execution
    publish(task_id, "status", "Code executed successfully.")
    return {
        **state,
        "execution_result": result["stdout"],
        "error": None,
        "error_type": None,
        "timed_out_code": "",
    }
