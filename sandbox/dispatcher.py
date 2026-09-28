# Project Midas — Tier B dispatcher sidecar microservice (sole owner of docker.sock)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
from fastapi import FastAPI, HTTPException, Header
from sandbox.job_spec import JobSpec
import docker
import logging
import os
import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DISPATCH_LOG = os.getenv("TIER_B_DISPATCH_LOG", "./tier_b_dispatch.log")
OUTPUTS_DIR = os.path.abspath(os.getenv("OUTPUTS_DIR", "./outputs"))
DISPATCHER_SECRET = os.getenv("DISPATCHER_SECRET", "")  # Internal shared secret between worker and dispatcher

app = FastAPI(title="Midas Tier B Dispatcher", docs_url=None, redoc_url=None)

try:
    docker_client = docker.from_env()
except Exception as e:
    logger.critical(f"Cannot connect to Docker socket: {e}")
    docker_client = None


def _log_dispatch_attempt(spec: JobSpec, user_id_hash: str, status: str) -> None:
    """Append one line to tier_b_dispatch.log before the container is launched.
    Written first so it survives even if the container itself crashes.
    Format: ISO_TS | user_id_hash=... | job_id=... | image=... | code_hash=... | status=...
    """
    line = (
        f"{datetime.datetime.utcnow().isoformat()} "
        f"| user_id_hash={user_id_hash} "
        f"| job_id={spec.job_id} "
        f"| image={spec.image} "
        f"| code_hash={spec.code_hash} "
        f"| status={status}\n"
    )
    with open(DISPATCH_LOG, "a") as f:
        f.write(line)


@app.post("/dispatch")
async def dispatch_job(
    spec: JobSpec,
    x_user_id_hash: str = Header(..., description="SHA-256 of the submitting user ID"),
    x_dispatcher_secret: str = Header(..., description="Shared internal secret"),
):
    # Verify internal secret — prevents anything other than the trusted worker from reaching this endpoint
    if DISPATCHER_SECRET and x_dispatcher_secret != DISPATCHER_SECRET:
        _log_dispatch_attempt(spec, x_user_id_hash, "rejected:bad_secret")
        raise HTTPException(status_code=403, detail="Invalid dispatcher secret")

    if docker_client is None:
        _log_dispatch_attempt(spec, x_user_id_hash, "rejected:no_docker")
        raise HTTPException(status_code=503, detail="Docker client unavailable")

    # Log BEFORE launching — this record must survive container crashes
    _log_dispatch_attempt(spec, x_user_id_hash, "accepted")
    logger.info(f"Tier B dispatch: job_id={spec.job_id} image={spec.image}")

    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    try:
        container = docker_client.containers.run(
            image=spec.image,
            command=["python", "-c", spec.code],
            detach=False,                    # Wait for completion
            network_disabled=True,           # Air-gap enforced inside the sandbox too
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,                 # 50% of one CPU core
            volumes={OUTPUTS_DIR: {"bind": "/outputs", "mode": "rw"}},
            timeout=spec.timeout_seconds,
            remove=True,                     # Auto-delete container after execution
        )
        # containers.run with detach=False returns bytes of stdout
        stdout = container.decode("utf-8", errors="replace") if isinstance(container, bytes) else str(container)
        return {"exit_code": 0, "stdout": stdout, "stderr": ""}
    except docker.errors.ContainerError as e:
        return {"exit_code": e.exit_status, "stdout": "", "stderr": e.stderr.decode("utf-8", errors="replace")}
    except Exception as e:
        logger.error(f"Dispatch failed for job {spec.job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
