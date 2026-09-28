# Project Midas - Pydantic v2 JobSpec model for Tier B dispatch API
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
from pydantic import BaseModel, Field, field_validator
import hashlib

ALLOWED_IMAGES = frozenset({"midas-sandbox:latest"})

class JobSpec(BaseModel):
    job_id: str = Field(..., description="UUID assigned by the submitting worker")
    image: str = Field(..., description="Docker image name - must be in ALLOWED_IMAGES")
    code: str = Field(..., description="Python source code to execute inside the container")
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    code_hash: str = Field(default="", description="SHA-256 of code, auto-computed if empty")

    @field_validator("image")
    @classmethod
    def image_must_be_allowed(cls, v: str) -> str:
        if v not in ALLOWED_IMAGES:
            raise ValueError(f"Image '{v}' is not in the dispatcher allowlist")
        return v

    def model_post_init(self, __context):
        object.__setattr__(self, "code_hash", hashlib.sha256(self.code.encode()).hexdigest())
