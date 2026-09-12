from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
from uuid import UUID

ProjectStatus = Literal[
    "DRAFT", "QUEUED", "ANALYZING", "GENERATING", "TESTING",
    "PREVIEW_READY", "AWAITING_APPROVAL", "DEPLOYING", "DEPLOYED",
    "GENERATION_FAILED", "TEST_FAILED", "PREVIEW_FAILED",
    "DEPLOY_FAILED", "ROLLED_BACK"
]

class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    idea: str = Field(min_length=20, max_length=30000)
    features: list[str] = []
    design_preferences: str = ""
    target_users: str = ""
    user_id: UUID | None = None

class RefinementCreate(BaseModel):
    request: str = Field(min_length=3, max_length=10000)

class Project(BaseModel):
    id: UUID
    title: str
    idea: str
    status: ProjectStatus
    preview_url: str | None = None
    production_url: str | None = None
    current_version: int = 0
    created_at: str | None = None
    updated_at: str | None = None

class AgentResult(BaseModel):
    agent: str
    summary: str = ""
    data: dict[str, Any] = {}
    files: dict[str, str] = {}

class BuildResult(BaseModel):
    ok: bool
    logs: str
    preview_url: str | None = None
    artifact_path: str | None = None

class DeploymentResult(BaseModel):
    ok: bool
    provider: str
    url: str | None = None
    deployment_id: str | None = None
    logs: str = ""
