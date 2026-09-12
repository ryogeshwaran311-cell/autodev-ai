from __future__ import annotations
import io, zipfile
import httpx
from app.config import get_settings
from app.schemas import DeploymentResult

class NetlifyDeployer:
    def __init__(self):
        self.settings = get_settings()

    async def deploy_preview(self, files: dict[str, str], project_name: str) -> DeploymentResult:
        if not self.settings.netlify_token:
            return DeploymentResult(
                ok=True, provider="netlify",
                url=f"http://localhost:5173/?preview={project_name}",
                deployment_id="mock-netlify-preview",
                logs="NETLIFY_TOKEN missing; returned local demo preview URL."
            )

        # This adapter expects built static files under frontend/dist/.
        static = {
            path.removeprefix("frontend/dist/"): content
            for path, content in files.items()
            if path.startswith("frontend/dist/")
        }
        if not static:
            return DeploymentResult(
                ok=False, provider="netlify",
                logs="No frontend/dist artifacts found. Build in Sandbox before real Netlify deploy."
            )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for path, content in static.items():
                z.writestr(path, content)
        buf.seek(0)

        headers = {"Authorization": f"Bearer {self.settings.netlify_token}"}
        async with httpx.AsyncClient(timeout=90) as client:
            site = await client.post("https://api.netlify.com/api/v1/sites", headers=headers, json={})
            site.raise_for_status()
            site_data = site.json()
            deploy = await client.post(
                f"https://api.netlify.com/api/v1/sites/{site_data['id']}/deploys",
                headers={**headers, "Content-Type": "application/zip"},
                content=buf.getvalue(),
            )
            deploy.raise_for_status()
            data = deploy.json()
        return DeploymentResult(
            ok=True, provider="netlify",
            url=data.get("deploy_ssl_url") or data.get("ssl_url") or data.get("url"),
            deployment_id=data.get("id"),
            logs="Netlify preview deployed"
        )
