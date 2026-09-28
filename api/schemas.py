# Project Midas — Pydantic Schemas
# Author: Atharva Kishor Jadhav (AJ)
from pydantic import BaseModel, ConfigDict

class TokenRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TaskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    prompt: str

class TaskResponse(BaseModel):
    task_id: str
    status: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: str | None = None
    output_path: str | None = None
    error: str | None = None

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str
