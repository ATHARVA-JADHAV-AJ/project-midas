# Project Midas — WebSocket event emitter / thought-stream broadcaster
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
# Cross-container event delivery via Redis Pub/Sub.
#
# Architecture:
#   - Celery worker (separate container) calls publish() to push events
#     to a Redis Pub/Sub channel per task_id.
#   - API container runs a subscriber loop per task_id that listens on
#     the Redis channel and forwards events to connected WebSockets.
#   - Direct in-process emit() is kept for any future single-process mode.
#
# This replaces the prior in-memory-only broadcast that was silently
# broken in Docker deployments (worker and API have separate memory spaces).

import os
import json
import asyncio
import logging
from typing import Dict, Set

import redis
from fastapi import WebSocket

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Synchronous Redis client for publish (called from Celery worker threads)
_redis_sync = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Registry: task_id -> set of active WebSocket connections (API process only)
_connections: Dict[str, Set[WebSocket]] = {}

# Track active subscriber tasks so we don't spawn duplicates
_subscriber_tasks: Dict[str, asyncio.Task] = {}


def _channel_name(task_id: str) -> str:
    return f"midas:stream:{task_id}"


# --------------- Publisher (called from Celery worker) -------------------

def publish(task_id: str, event_type: str, payload: str) -> None:
    """Publish a thought-stream event to Redis Streams.

    This is a SYNCHRONOUS function — safe to call from Celery worker
    threads without needing asyncio.run().
    """
    frame = json.dumps({
        "event_type": event_type,
        "task_id": task_id,
        "payload": payload,
    })
    try:
        key = _channel_name(task_id)
        _redis_sync.xadd(key, {"payload": frame}, maxlen=1000)
        # Extend TTL to 1 hour after every event
        _redis_sync.expire(key, 3600)
    except Exception as e:
        # Never let a stream failure crash the agent pipeline
        logger.warning(f"Failed to publish stream event for {task_id}: {e}")

def publish_monitor_event(task_id: str, username: str, role: str, tier: int, event_type: str, payload: str) -> None:
    """Publish to the monitoring stream so admins can watch subordinate activity."""
    from datetime import datetime, timezone
    frame = json.dumps({
        "task_id": task_id,
        "username": username,
        "role": role,
        "tier": tier,
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    try:
        key = f"midas:monitor:tier:{tier}"
        _redis_sync.xadd(key, {"payload": frame}, maxlen=500)
        _redis_sync.expire(key, 7200)  # 2 hour TTL
    except Exception as e:
        logger.warning("Failed to publish monitor event: %s", e)


def get_monitor_events(caller_tier: int, limit: int = 50, since_seconds: int = 0) -> list:
    """Read monitoring events for all tiers below caller_tier."""
    results = []
    for subordinate_tier in range(caller_tier + 1, 6):
        key = f"midas:monitor:tier:{subordinate_tier}"
        try:
            if since_seconds > 0:
                import time
                min_id = f"{int((time.time() - since_seconds) * 1000)}-0"
                entries = _redis_sync.xrange(key, min=min_id, count=limit)
            else:
                entries = _redis_sync.xrange(key, count=limit)
            for entry_id, data in entries:
                payload = data.get("payload", "{}")
                results.append(json.loads(payload))
        except Exception:
            pass
    return results


# --------------- Subscriber (runs in API process) ------------------------

async def _subscriber_loop(task_id: str) -> None:
    """Background task: read from the Redis stream for task_id and
    forward events to all connected WebSockets.

    Runs until the last WebSocket for this task_id disconnects.
    """
    channel = _channel_name(task_id)
    last_id = "0-0"
    logger.info(f"Redis stream subscriber started for {task_id}")
    try:
        while task_id in _connections and _connections[task_id]:
            # Blocking read with timeout to allow checking
            # if connections are still alive
            def read_stream():
                return _redis_sync.xread({channel: last_id}, count=10, block=500)

            messages = await asyncio.get_event_loop().run_in_executor(
                None, read_stream
            )

            if messages:
                for _, stream_messages in messages:
                    for msg_id, msg_data in stream_messages:
                        last_id = msg_id
                        frame = msg_data.get("payload")
                        if not frame:
                            continue

                        dead: Set[WebSocket] = set()
                        for ws in _connections.get(task_id, set()):
                            try:
                                await ws.send_text(frame)
                            except Exception:
                                dead.add(ws)
                        for ws in dead:
                            _connections[task_id].discard(ws)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Subscriber loop error for {task_id}: {e}")
    finally:
        _subscriber_tasks.pop(task_id, None)
        logger.info(f"Redis stream subscriber stopped for {task_id}")


async def start_subscriber(task_id: str) -> None:
    """Spawn the Redis subscriber background task if not already running."""
    if task_id not in _subscriber_tasks or _subscriber_tasks[task_id].done():
        _subscriber_tasks[task_id] = asyncio.create_task(_subscriber_loop(task_id))


async def stop_subscriber(task_id: str) -> None:
    """Cancel the subscriber task if no more WebSocket connections remain."""
    if task_id in _connections and not _connections[task_id]:
        task = _subscriber_tasks.pop(task_id, None)
        if task and not task.done():
            task.cancel()


# --------------- WebSocket registration (API process only) ---------------

async def register(task_id: str, ws: WebSocket) -> None:
    """Add a WebSocket to the broadcast list and ensure the subscriber is running."""
    _connections.setdefault(task_id, set()).add(ws)
    await start_subscriber(task_id)


async def unregister(task_id: str, ws: WebSocket) -> None:
    """Remove a WebSocket and clean up subscriber if it was the last one."""
    if task_id in _connections:
        _connections[task_id].discard(ws)
        if not _connections[task_id]:
            del _connections[task_id]
            await stop_subscriber(task_id)


# --------------- Direct emit (kept for in-process use) -------------------

async def emit(task_id: str, event_type: str, payload: str) -> None:
    """Broadcast directly to in-process WebSocket connections.

    This is used when the caller is in the same process as the API.
    For cross-container delivery (Celery worker -> API), use publish().
    """
    frame = json.dumps({
        "event_type": event_type,
        "task_id": task_id,
        "payload": payload,
    })

    dead: Set[WebSocket] = set()
    for ws in _connections.get(task_id, set()):
        try:
            await ws.send_text(frame)
        except Exception:
            dead.add(ws)

    for ws in dead:
        _connections[task_id].discard(ws)
