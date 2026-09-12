from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import ProjectCreate, RefinementCreate
from app.store import store
from app.orchestrator import orchestrator
from supabase_client import supabase


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="AutoDev AI API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RATE LIMITING
# ============================================================

_hits = defaultdict(deque)

RATE_WINDOW = 60
RATE_MAX = 20


@app.middleware("http")
async def rate_limit(request: Request, call_next):

    if request.url.path in (
        "/health",
        "/health/supabase",
    ):
        return await call_next(request)

    key = (
        request.client.host
        if request.client
        else "unknown"
    )

    now = time.time()
    queue = _hits[key]

    while queue and queue[0] < now - RATE_WINDOW:
        queue.popleft()

    if len(queue) >= RATE_MAX:
        return JSONResponse(
            {
                "detail": "Rate limit exceeded"
            },
            status_code=429,
        )

    queue.append(now)

    return await call_next(request)


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "autodev-ai-api",
    }


# ============================================================
# SUPABASE HEALTH
# ============================================================

@app.get("/health/supabase")
def health_supabase():

    if supabase is None:
        return {
            "status": "ok",
            "service": "supabase",
            "connected": False,
            "rows_checked": 0,
        }

    try:

        result = (
            supabase
            .table("projects")
            .select("id")
            .limit(1)
            .execute()
        )

        rows_checked = (
            len(result.data)
            if result.data
            else 0
        )

        return {
            "status": "ok",
            "service": "supabase",
            "connected": True,
            "rows_checked": rows_checked,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Supabase connection failed: {exc}",
        )


# ============================================================
# CREATE PROJECT
# ============================================================

@app.post(
    "/api/projects",
    status_code=201,
)
def create_project(
    payload: ProjectCreate,
):

    try:

        return store.create_project(
            payload.model_dump()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# LIST PROJECTS
# ============================================================

@app.get("/api/projects")
def list_projects():

    try:

        return store.list_projects()

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# GET PROJECT
# ============================================================

@app.get(
    "/api/projects/{project_id}"
)
def get_project(
    project_id: str,
):

    project = store.get_project(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


# ============================================================
# PROJECT LOGS
# ============================================================

@app.get(
    "/api/projects/{project_id}/logs"
)
def get_logs(
    project_id: str,
):

    if not store.get_project(project_id):

        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return store.logs(project_id)


# ============================================================
# PROJECT ARTIFACTS
# ============================================================

@app.get(
    "/api/projects/{project_id}/artifacts"
)
def get_artifacts(
    project_id: str,
):

    project = store.get_project(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    version = int(
        project.get("current_version")
        or 0
    )

    if version <= 0:

        return {
            "project_id": project_id,
            "version": 0,
            "files": {},
        }

    files = store.get_artifacts(
        project_id,
        version,
    )

    return {
        "project_id": project_id,
        "version": version,
        "files": files,
    }


# ============================================================
# START PROJECT GENERATION
# ============================================================

@app.post(
    "/api/projects/{project_id}/generate",
    status_code=202,
)
async def generate_project(
    project_id: str,
    background_tasks: BackgroundTasks,
):

    project = store.get_project(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    store.update_project(
        project_id,
        status="QUEUED",
    )

    background_tasks.add_task(
        orchestrator.generate,
        project_id,
    )

    return {
        "queued": True,
        "project_id": project_id,
        "message": "AI project generation queued",
    }


# ============================================================
# REFINE PROJECT
# ============================================================

@app.post(
    "/api/projects/{project_id}/refine",
    status_code=202,
)
async def refine_project(
    project_id: str,
    payload: RefinementCreate,
    background_tasks: BackgroundTasks,
):

    if not store.get_project(project_id):

        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    background_tasks.add_task(
        orchestrator.refine,
        project_id,
        payload.request,
    )

    return {
        "queued": True,
        "project_id": project_id,
        "message": "Refinement queued",
    }


# ============================================================
# APPROVE PROJECT
# ============================================================

@app.post(
    "/api/projects/{project_id}/approve"
)
async def approve_project(
    project_id: str,
):

    try:

        result = await orchestrator.approve(
            project_id
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    if not result:

        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return result


# ============================================================
# ROLLBACK PROJECT
# ============================================================

@app.post(
    "/api/projects/{project_id}/rollback"
)
def rollback_project(
    project_id: str,
):

    project = store.get_project(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    store.update_project(
        project_id,
        status="ROLLED_BACK",
    )

    store.log(
        project_id,
        "rollback",
        (
            "Rollback requested. "
            "Provider-specific promotion hook required."
        ),
    )

    return store.get_project(
        project_id
    )