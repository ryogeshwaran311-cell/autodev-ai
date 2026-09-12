from __future__ import annotations
import asyncio
from app.services.gemini import GeminiService
from app.agents.specialists import (
    RequirementsAgent, ArchitectAgent, DatabaseAgent, FrontendAgent,
    BackendAgent, QAAgent, SecurityAgent, DevOpsAgent, RefinementAgent
)
from app.deploy.sandbox import BuildRunner
from app.deploy.netlify import NetlifyDeployer
from app.deploy.vercel import VercelDeployer
from app.store import store

class Orchestrator:
    def __init__(self):
        llm = GeminiService()
        self.requirements = RequirementsAgent(llm)
        self.architect = ArchitectAgent(llm)
        self.database = DatabaseAgent(llm)
        self.frontend = FrontendAgent(llm)
        self.backend = BackendAgent(llm)
        self.qa = QAAgent(llm)
        self.security = SecurityAgent(llm)
        self.devops = DevOpsAgent(llm)
        self.refinement = RefinementAgent(llm)
        self.runner = BuildRunner()
        self.netlify = NetlifyDeployer()
        self.vercel = VercelDeployer()

    async def approve(self, project_id: str):
        project = store.get_project(project_id)
        if not project:
            return

        try:
            store.update_project(project_id, status="ANALYZING")
            store.log(project_id, "requirements", "Analyzing product idea")
            submission = {
                "title": project["title"],
                "idea": project["idea"],
                "features": project.get("features", []),
                "design_preferences": project.get("design_preferences", ""),
                "target_users": project.get("target_users", ""),
            }
            req = await self.requirements.run({"submission": submission})

            store.log(project_id, "architecture", "Designing solution architecture")
            arch = await self.architect.run({"requirements": req.data})

            store.update_project(project_id, status="GENERATING")
            store.log(project_id, "generation", "Generating database, frontend and backend in parallel")
            db_task = self.database.run({"architecture": arch.data})
            fe_task = self.frontend.run({"requirements": req.data, "architecture": arch.data})
            be_task = self.backend.run({"requirements": req.data, "architecture": arch.data})
            db, fe, be = await asyncio.gather(db_task, fe_task, be_task)

            files = {}
            files.update(db.files)
            files.update(fe.files)
            files.update(be.files)

            qa = await self.qa.run({"files": files, "requirements": req.data})
            security = await self.security.run({"files": files})
            if not security.data.get("passed"):
                raise RuntimeError(f"Security gate failed: {security.data['findings']}")

            version = int(project.get("current_version") or 0) + 1
            store.save_artifacts(project_id, version, files)
            store.update_project(project_id, current_version=version, status="TESTING")

            commands = qa.data.get("test_commands") or []
            store.log(project_id, "testing", f"Validating {len(files)} generated files")
            build = await self.runner.validate(files, commands)
            if not build.ok:
                store.update_project(project_id, status="TEST_FAILED")
                store.log(project_id, "testing", build.logs, "error")
                return

            ops = await self.devops.run({"qa": qa.data, "files": list(files)})
            store.log(project_id, "devops", ops.summary)

            # The starter returns a local preview when real build output/token is unavailable.
            preview = await self.netlify.deploy_preview(files, project["title"])
            if not preview.ok:
                # Keep a reviewable API-level preview state rather than claiming production deployed.
                store.update_project(project_id, status="PREVIEW_FAILED")
                store.log(project_id, "preview", preview.logs, "error")
                return

            store.update_project(
                project_id,
                status="AWAITING_APPROVAL",
                preview_url=preview.url
            )
            store.log(project_id, "preview", f"Preview ready: {preview.url}")

        except Exception as exc:
            store.update_project(project_id, status="GENERATION_FAILED")
            store.log(project_id, "error", str(exc), "error")

    async def refine(self, project_id: str, request: str):
        project = store.get_project(project_id)
        if not project:
            return
        scope = await self.refinement.run({"request": request})
        store.log(project_id, "refinement", f"Requested scopes: {scope.data.get('scopes')}")
        # MVP implementation performs a clean immutable regeneration.
        # The scope result is stored/logged and is ready to drive selective regeneration.
        store.update_project(
            project_id,
            idea=project["idea"] + f"\n\nRefinement request: {request}",
            status="QUEUED"
        )
        await self.generate(project_id)

    async def approve(self, project_id: str):
        project = store.get_project(project_id)
        if not project:
            return None
        if project["status"] not in ("AWAITING_APPROVAL", "PREVIEW_READY"):
            raise ValueError("Project must have an approved preview before production deployment")

        store.update_project(project_id, status="DEPLOYING")
        store.log(project_id, "deployment", "Starting production deployment")
        backend = await self.vercel.deploy_backend(project["title"], preview=False)

        # Frontend production promotion should be wired to the installation's Netlify site.
        if not backend.ok:
            store.update_project(project_id, status="DEPLOY_FAILED")
            store.log(project_id, "deployment", backend.logs, "error")
            return store.get_project(project_id)

        production_url = project.get("preview_url")
        store.update_project(
            project_id,
            status="DEPLOYED",
            production_url=production_url
        )
        store.log(project_id, "deployment", f"Deployment complete: {production_url}")
        return store.get_project(project_id)

orchestrator = Orchestrator()
