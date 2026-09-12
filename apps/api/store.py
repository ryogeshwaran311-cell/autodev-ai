from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Any
from app.config import get_settings

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    """
    Supabase-backed when configured; in-memory fallback for local demo.
    """
    def __init__(self):
        self.settings = get_settings()
        self._projects: dict[str, dict] = {}
        self._logs: dict[str, list[dict]] = {}
        self._artifacts: dict[str, dict[str, str]] = {}
        self._supabase = None

        if self.settings.supabase_url and self.settings.supabase_service_role_key:
            from supabase import create_client
            self._supabase = create_client(
                self.settings.supabase_url,
                self.settings.supabase_service_role_key
            )

    def create_project(self, payload: dict) -> dict:
        project = {
            "id": str(uuid4()),
            "user_id": str(payload["user_id"]) if payload.get("user_id") else None,
            "title": payload["title"],
            "idea": payload["idea"],
            "features": payload.get("features", []),
            "design_preferences": payload.get("design_preferences", ""),
            "target_users": payload.get("target_users", ""),
            "status": "DRAFT",
            "preview_url": None,
            "production_url": None,
            "current_version": 0,
            "created_at": now(),
            "updated_at": now(),
        }
        if self._supabase:
            row = self._supabase.table("projects").insert(project).execute().data[0]
            return row
        self._projects[project["id"]] = project
        return project

    def list_projects(self) -> list[dict]:
        if self._supabase:
            return self._supabase.table("projects").select("*").order("created_at", desc=True).execute().data
        return sorted(self._projects.values(), key=lambda x: x["created_at"], reverse=True)

    def get_project(self, project_id: str) -> dict | None:
        if self._supabase:
            rows = self._supabase.table("projects").select("*").eq("id", project_id).limit(1).execute().data
            return rows[0] if rows else None
        return self._projects.get(project_id)

    def update_project(self, project_id: str, **changes) -> dict:
        changes["updated_at"] = now()
        if self._supabase:
            rows = self._supabase.table("projects").update(changes).eq("id", project_id).execute().data
            return rows[0]
        self._projects[project_id].update(changes)
        return self._projects[project_id]

    def log(self, project_id: str, stage: str, message: str, level: str = "info"):
        entry = {
            "project_id": project_id, "stage": stage, "message": message,
            "level": level, "created_at": now()
        }
        if self._supabase:
            self._supabase.table("build_logs").insert(entry).execute()
        else:
            self._logs.setdefault(project_id, []).append(entry)

    def logs(self, project_id: str) -> list[dict]:
        if self._supabase:
            return self._supabase.table("build_logs").select("*").eq("project_id", project_id).order("created_at").execute().data
        return self._logs.get(project_id, [])

    def save_artifacts(self, project_id: str, version: int, files: dict[str, str]):
        key = f"{project_id}:{version}"
        self._artifacts[key] = files
        if self._supabase:
            rows = [{
                "project_id": project_id,
                "version_number": version,
                "path": path,
                "content": content,
                "kind": path.split("/", 1)[0] if "/" in path else "root",
            } for path, content in files.items()]
            if rows:
                self._supabase.table("artifacts").insert(rows).execute()

    def get_artifacts(self, project_id: str, version: int) -> dict[str, str]:
        key = f"{project_id}:{version}"
        if key in self._artifacts:
            return self._artifacts[key]
        if self._supabase:
            rows = self._supabase.table("artifacts").select("path,content").eq(
                "project_id", project_id
            ).eq("version_number", version).execute().data
            return {r["path"]: r["content"] for r in rows}
        return {}

store = Store()
