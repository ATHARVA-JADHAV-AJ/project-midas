# Project Midas — Priority consumer loop
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
# Dedicated consumer loop — runs as its own process:
#   python -m task_queue.consumer
#
# Why a separate consumer instead of a standard Celery broker queue?
# Our queue lives in a Redis Sorted Set (not a standard list/stream) so that
# we can implement time-decay priority. Celery has no native Sorted Set
# consumer, so this loop bridges the gap: ZPOPMIN -> send_task -> Celery worker.

import time
import logging
from task_queue.queue_manager import pop_next_task, set_task_status
from task_queue.worker import celery_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# How long to sleep when the Sorted Set is empty.
# 0.5 s is a good balance: low latency for interactive tasks, trivial CPU cost.
POLL_INTERVAL = 0.5  # seconds


def run() -> None:
    """Blocking loop — pops tasks by priority and hands them off to Celery.

    Only sleeps when the queue is empty; otherwise it drains continuously so
    bursts of high-priority tasks are dispatched without artificial delay.
    """
    logger.info("Midas priority consumer started — polling Sorted Set")
    while True:
        task = pop_next_task()

        if task:
            task_id = task["task_id"]
            role    = task.get("role", "unknown")
            logger.info(f"Dispatching task {task_id} (role={role})")

            # Mark running *before* send_task so the status hash is never stale
            # from the API perspective between pop and Celery pickup.
            set_task_status(task_id, "running")

            celery_app.send_task(
                "task_queue.tasks.run_agent_task",
                args=[task_id, task["prompt"]],
            )
        else:
            # Queue is empty — yield CPU rather than busy-waiting
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
