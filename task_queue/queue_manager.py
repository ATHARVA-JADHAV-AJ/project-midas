# Project Midas — Priority queue manager (Redis Sorted Set backend)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------

import redis
import os
import time
from typing import Literal

# --- Score constants -----------------------------------------------------------
# Base scores separate tiers; lower score = higher priority in ZPOPMIN.
ROLE_BASE_SCORE: dict[str, float] = {
    "admin":   0,      # always first
    "analyst": 1000,   # mid tier
    "default": 2000,   # lowest tier
}

# AGING_RATE derivation: tiers are spaced 1000 points apart (see ROLE_BASE_SCORE
# above). We want a task in a lower tier to overtake a FRESH task in the
# tier above it after exactly 300s of waiting. 1000 / 300 = 3.33.
# This is exposed as MIDAS_AGING_RATE so it can be retuned without a
# code change if the 300s target ever needs adjusting.
AGING_RATE = float(os.environ.get("MIDAS_AGING_RATE", "3.33"))

SORT_KEY = "midas:task_queue"  # the single Redis Sorted Set that drives the queue

# Redis client — URL comes from env so containers can override without code changes
_redis = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
)


# --- Internal helpers ----------------------------------------------------------

def _compute_score(role: str, submitted_at: float) -> float:
    """Compute the Sorted Set score for a task.

    Lower score = higher dequeue priority.
    Older tasks of any tier naturally rise above freshly submitted lower-tier tasks
    because elapsed time erodes the base score at ALPHA units per second.
    """
    elapsed = time.time() - submitted_at
    base = ROLE_BASE_SCORE.get(role, 2000)  # unknown roles treated as default
    return base - (AGING_RATE * elapsed)


# --- Public API ---------------------------------------------------------------

def enqueue(task_id: str, prompt: str, role: str, user: str = "") -> None:
    """Push a task onto the priority Sorted Set and store its metadata hash.

    Metadata lives in a separate hash (midas:task:{task_id}) so the worker
    can retrieve the full payload after ZPOPMIN returns only the task_id.
    Both writes are pipelined to keep them atomic from the caller's perspective.
    """
    submitted_at = time.time()
    score = _compute_score(role, submitted_at)

    pipe = _redis.pipeline()

    # Store full task payload; ZPOPMIN gives us only the task_id
    pipe.hset(f"midas:task:{task_id}", mapping={
        "status":       "queued",
        "prompt":       prompt,
        "role":         role,
        "user":         user,
        "submitted_at": str(submitted_at),
    })

    # Add to Sorted Set — value is task_id, score drives dequeue order
    pipe.zadd(SORT_KEY, {task_id: score})

    pipe.execute()


def set_task_status(task_id: str, status: str, **kwargs) -> None:
    """Update status and any additional fields on the task metadata hash.

    Extra kwargs (e.g. result=, error=, output_path=) are coerced to str
    because Redis hashes store only string values.
    """
    mapping = {"status": status, **{k: str(v) for k, v in kwargs.items()}}
    _redis.hset(f"midas:task:{task_id}", mapping=mapping)


def get_task_status(task_id: str) -> dict | None:
    """Return the full metadata hash for a task.

    Returns None for missing tasks.
    """
    data = _redis.hgetall(f"midas:task:{task_id}")
    if not data:
        return None
    return data


def pop_next_task() -> dict | None:
    """Pop the highest-priority task from the Sorted Set.

    ZPOPMIN atomically removes and returns the member with the lowest score,
    which corresponds to the highest-priority task under our scoring scheme.
    Returns the full metadata dict (augmented with task_id), or None if empty.
    """
    result = _redis.zpopmin(SORT_KEY, 1)
    if not result:
        return None

    task_id, score = result[0]
    data = _redis.hgetall(f"midas:task:{task_id}")
    data["task_id"] = task_id  # attach id so the consumer does not need a second lookup
    return data
