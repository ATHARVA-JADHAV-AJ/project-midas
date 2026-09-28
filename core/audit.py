# Project Midas — Audit Log Writer
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Appends structured audit entries to audit.jsonl.

Entry schema:
  timestamp       : ISO 8601 UTC
  task_id         : UUID of the task
  user_id_hash    : SHA-256 of the user's sub claim (no plaintext identity at rest)
  intent          : vision | math | document
  result_type     : success | failed
  output_path     : path to generated file, or null
  ground_score    : cosine similarity score from groundedness check (0.0–1.0), or null
  is_grounded     : bool
  iterations      : number of reasoning attempts used
  duration_ms     : wall time from task start to output write
  tier_b_dispatched : bool — always False for agent-generated tasks (Tier A only)

This file is append-only. Do not rotate or truncate it manually;
archive it by moving and starting a fresh file if size becomes a concern.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG", "./audit.jsonl"))


def log_audit_event(event: dict[str, Any]) -> None:
    """
    Append one structured JSON line to audit.jsonl.
    Adds the current UTC timestamp automatically.
    Safe for concurrent appends (each write is a single os.write call,
    which is atomic on POSIX for small payloads).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    line = json.dumps(entry, default=str) + "\n"
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        # Log to stderr but don't let an audit failure crash the task
        logger.error(f"Failed to write audit log entry: {e}")
