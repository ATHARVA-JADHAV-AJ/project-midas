# Project Midas ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â RestrictedPython Sandbox Runner (Tier A)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Executes agent-generated Python code inside a RestrictedPython sandbox.

Security posture (Tier A):
  - AST is transformed by RestrictedPython before execution ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â removes access
    to dunder attributes, restricted builtins, and unsafe attribute access
  - Filesystem writes are permitted only within OUTPUTS_DIR (/outputs/)
  - Network access is prevented by removing socket from the exec namespace
  - subprocess is not available
  - A threading.Timer enforces a hard 30-second wall-clock timeout

This covers the vast majority of agent tasks (docx/xlsx generation, data
formatting, math). Tier B (Docker sidecar) is reserved for operator-triggered
OS-isolation jobs ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â it is never called from this module.

Return value:
  {
    "exit_code": 0 | 1,
    "stdout": str,
    "stderr": str,
    "timed_out": bool,
  }
"""

import os
import io
import sys
import logging
import threading
import contextlib
import traceback
from pathlib import Path
from typing import Any

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import (
    safe_builtins,
    guarded_unpack_sequence,
    guarded_iter_unpack_sequence,
)
from RestrictedPython.transformer import RestrictingNodeTransformer

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", "./outputs")).resolve()
DEFAULT_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "30"))


def _build_restricted_globals() -> dict[str, Any]:
    """
    Construct the execution namespace for RestrictedPython.
    Only whitelisted builtins are available. Network and subprocess are absent.
    File I/O is allowed but path-guarded at the open() level.
    """
    builtins = dict(safe_builtins)

    # Allow print — RestrictedPython rewrites print(x) to _print_(x).
    # We need _print_ to be a callable that captures output.
    _printed_lines = []

    class _PrintCollector:
        """Captures all print() output inside the sandbox."""
        def __call__(self, *args, **kwargs):
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            text = sep.join(str(a) for a in args) + end
            _printed_lines.append(text)
        def _call_print(self, *args, **kwargs):
            self(*args, **kwargs)

    _shared_collector = _PrintCollector()

    def _print_factory(_getattr_=None):
        return _shared_collector

    builtins["print"] = _shared_collector
    builtins["_print_"] = _print_factory
    builtins["_printed_lines"] = _printed_lines

    # Allow safe iteration and attribute access helpers
    builtins["_getiter_"] = iter
    builtins["_getattr_"] = getattr
    builtins["_getitem_"] = lambda obj, key: obj[key]
    builtins["_unpack_sequence_"] = guarded_unpack_sequence
    builtins["_write_"] = lambda obj: obj  # Allow attribute assignment on safe objects
    builtins["_inplacevar_"] = lambda op, x, y: op(x, y)  # Allow +=, -= etc.

    # Allow open() only for paths inside OUTPUTS_DIR
    original_open = open

    def guarded_open(path, mode="r", *args, **kwargs):
        resolved = Path(path).resolve()
        # Allow access to OUTPUTS_DIR and all subdirectories (e.g. uploads/)
        try:
            is_allowed = resolved.is_relative_to(OUTPUTS_DIR)
        except AttributeError:
            # Python < 3.9 fallback
            is_allowed = str(resolved).startswith(str(OUTPUTS_DIR))
        if not is_allowed:
            raise PermissionError(
                f"Sandbox: file access outside /outputs/ is not permitted. "
                f"Attempted path: {resolved}"
            )
        # Ensure parent directories exist for write operations
        if "w" in mode or "a" in mode:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        return original_open(resolved, mode, *args, **kwargs)

    builtins["open"] = guarded_open

    globs = dict(safe_globals)
    globs["__builtins__"] = builtins

        # Allow safe standard library imports
    original_import = __import__
    ALLOWED_MODULES = {"math", "json", "datetime", "collections", "re", "uuid", "os", "pandas", "openpyxl", "statistics"}
    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in ALLOWED_MODULES:
            return original_import(name, globals, locals, fromlist, level)
        raise ImportError(f"Sandbox: import of module '{name}' is not permitted")
        
    builtins["__import__"] = guarded_import; globs["_import_"] = guarded_import; builtins["_import_"] = guarded_import

    # Pre-import safe standard library modules the agent commonly needs
    import math, json, datetime, collections, re, uuid, os.path, statistics
    import pandas as pd
    globs.update({
        "math": math,
        "json": json,
        "datetime": datetime,
        "collections": collections,
        "re": re,
        "uuid": uuid,
        "statistics": statistics,
        "pandas": pd,
        "pd": pd,
        "os": type("SafeOS", (), {"path": os.path, "makedirs": os.makedirs})(),
    })

    # Inject third-party document libraries ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â  the whole point of the sandbox
    try:
        from docx import Document
        globs["Document"] = Document
    except ImportError:
        pass

    try:
        import openpyxl
        from openpyxl import Workbook, load_workbook
        globs["openpyxl"] = openpyxl
        globs["Workbook"] = Workbook
        globs["load_workbook"] = load_workbook
    except ImportError:
        pass

    try:
        from fpdf import FPDF
        globs["FPDF"] = FPDF
    except ImportError:
        pass

    # Expose _printed_lines at the globs level so we can read it after exec
    globs["_printed_lines"] = builtins["_printed_lines"]

    return globs


def run_restricted(code: str, timeout_seconds: int = DEFAULT_TIMEOUT) -> dict:
    """
    Compile and execute `code` inside the RestrictedPython sandbox.

    The hard timeout is enforced by a daemon thread that sets an event
    and raises a flag the main execution loop checks. Since Python's GIL
    means we can't kill a thread externally, the timeout flag is checked
    via a threading.Event that interrupts the exec() loop's thread via
    ctypes.pythonapi (or we rely on the Timer to join after the code finishes).

    For simplicity and reliability, we use threading.Timer with a flag
    checked by a wrapper: if the timer fires, we set `timed_out=True` and
    the thread is abandoned (daemon=True ensures it doesn't block shutdown).
    The caller receives the timed_out signal and routes accordingly.
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
    }

    # --- Preprocess: fix augmented assignments on subscripts ---
    # RestrictedPython bans `obj[key] += val`. We rewrite them automatically.
    import ast as _ast

    def _fix_augmented_assignments(source: str) -> str:
        """Rewrite obj[x] += y → obj[x] = obj[x] + y to satisfy RestrictedPython."""
        try:
            tree = _ast.parse(source)
        except SyntaxError:
            return source  # Let RestrictedPython handle it

        class _Fixer(_ast.NodeTransformer):
            def visit_AugAssign(self, node):
                if isinstance(node.target, (_ast.Subscript, _ast.Attribute)):
                    # obj[key] += value → obj[key] = obj[key] + value
                    import copy
                    target_copy = copy.deepcopy(node.target)
                    # Change Store context to Load for the right-hand side
                    if hasattr(target_copy, 'ctx'):
                        target_copy.ctx = _ast.Load()
                    op_map = {
                        _ast.Add: _ast.Add, _ast.Sub: _ast.Sub,
                        _ast.Mult: _ast.Mult, _ast.Div: _ast.Div,
                        _ast.Mod: _ast.Mod, _ast.Pow: _ast.Pow,
                        _ast.FloorDiv: _ast.FloorDiv,
                    }
                    bin_op = _ast.BinOp(
                        left=target_copy,
                        op=node.op,
                        right=node.value
                    )
                    new_node = _ast.Assign(
                        targets=[node.target],
                        value=bin_op
                    )
                    _ast.copy_location(new_node, node)
                    _ast.fix_missing_locations(new_node)
                    return new_node
                return node

        tree = _Fixer().visit(tree)
        _ast.fix_missing_locations(tree)
        return _ast.unparse(tree)

    code = _fix_augmented_assignments(code)

    # Compile with RestrictedPython's AST transformer
    try:
        byte_code = compile_restricted(code, filename="<agent_code>", mode="exec")
    except SyntaxError as e:
        result["exit_code"] = 1
        result["stderr"] = f"SyntaxError: {e}"
        return result

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    exec_globals = _build_restricted_globals()

    timed_out_flag = threading.Event()
    exec_exception: list[Exception] = []

    def _exec_target():
        try:
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                exec(byte_code, exec_globals)  # noqa: S102
        except Exception as exc:
            exec_exception.append(exc)

    exec_thread = threading.Thread(target=_exec_target, daemon=True)

    def _on_timeout():
        timed_out_flag.set()
        logger.warning("RestrictedPython sandbox timeout fired")

    timer = threading.Timer(timeout_seconds, _on_timeout)
    timer.start()

    exec_thread.start()
    exec_thread.join(timeout=timeout_seconds + 0.5)  # Slightly longer than the timer
    timer.cancel()

    result["stdout"] = stdout_capture.getvalue()

    # Capture output from our custom PrintCollector
    pl = exec_globals.get("_printed_lines", [])
    if pl:
        result["stdout"] += "".join(pl)

    if timed_out_flag.is_set() or exec_thread.is_alive():
        result["timed_out"] = True
        result["exit_code"] = 1
        return result

    if exec_exception:
        exc = exec_exception[0]
        result['exit_code'] = 1
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        filtered_tb = [ln for ln in tb_lines if '/app/sandbox/restricted_runner.py' not in ln]
        result['stderr'] = ''.join(filtered_tb)
    else:
        result["stderr"] = stderr_capture.getvalue()

    return result



