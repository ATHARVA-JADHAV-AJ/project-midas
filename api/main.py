# Project Midas — FastAPI application factory
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.router import router
from api.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Project Midas API starting — air-gap enforced, all models local")
    init_db()  # Ensure tables exist
    yield
    logger.info("Project Midas API shutting down")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Project Midas",
    description="Air-gapped agentic OS — Atharva Kishor Jadhav (AJ)",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

from api.system_stats import router as stats_router
app.include_router(stats_router)

