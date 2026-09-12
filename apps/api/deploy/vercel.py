from __future__ import annotations
from app.config import get_settings
from app.schemas import DeploymentResult

class VercelDeployer:
    """
    Control-plane adapter.

    In a production installation, generated backend code should be pushed to
    a dedicated repository/project or deployed through Vercel's deployment API.
    This starter records a mock deployment when VERCEL_TOKEN is absent.
    """
    def __init__(self):
        self.settings = get_settings()

    async def deploy_backend(self, project_name: str, preview: bool = True) -> DeploymentResult:
        if not self.settings.vercel_token:
            return DeploymentResult(
                ok=True,
                provider="vercel",
                url="http://localhost:8000",
                deployment_id="mock-vercel-backend",
                logs="VERCEL_TOKEN missing; backend deployment is mocked."
            )
        return DeploymentResult(
            ok=False,
            provider="vercel",
            logs=(
                "VERCEL_TOKEN is configured, but repository/project binding is intentionally "
                "left installation-specific. Connect this adapter to your Vercel project/repo "
                "or deployment API before enabling autonomous production deploys."
            )
        )
