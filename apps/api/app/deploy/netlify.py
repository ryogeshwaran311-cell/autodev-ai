from __future__ import annotations

import asyncio
import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import httpx

from app.config import get_settings
from app.schemas import DeploymentResult


class NetlifyDeployer:
    def __init__(self):
        self.settings = get_settings()

    async def deploy_preview(
        self,
        files: dict[str, str],
        project_name: str
    ) -> DeploymentResult:

        if not self.settings.netlify_token:
            return DeploymentResult(
                ok=True,
                provider="netlify",
                url=f"http://localhost:5173/?preview={project_name}",
                deployment_id="mock-netlify-preview",
                logs="NETLIFY_TOKEN missing; returned local demo preview URL.",
            )

        try:
            static = await asyncio.to_thread(
                self._build_frontend,
                files
            )
        except Exception as exc:
            return DeploymentResult(
                ok=False,
                provider="netlify",
                logs=f"Frontend build failed: {exc}",
            )

        if not static:
            return DeploymentResult(
                ok=False,
                provider="netlify",
                logs="Frontend build produced no files.",
            )

        # Create ZIP containing the Vite dist/ contents
        buf = io.BytesIO()

        with zipfile.ZipFile(
            buf,
            "w",
            zipfile.ZIP_DEFLATED
        ) as z:
            for path, content in static.items():
                z.writestr(path, content)

        buf.seek(0)

        headers = {
            "Authorization": f"Bearer {self.settings.netlify_token}"
        }

        try:
            async with httpx.AsyncClient(timeout=90) as client:

                # Create a Netlify site
                site = await client.post(
                    "https://api.netlify.com/api/v1/sites",
                    headers=headers,
                    json={},
                )

                site.raise_for_status()

                site_data = site.json()

                # Deploy the built frontend
                deploy = await client.post(
                    f"https://api.netlify.com/api/v1/sites/{site_data['id']}/deploys",
                    headers={
                        **headers,
                        "Content-Type": "application/zip",
                    },
                    content=buf.getvalue(),
                )

                deploy.raise_for_status()

                data = deploy.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:1000]

            return DeploymentResult(
                ok=False,
                provider="netlify",
                logs=(
                    f"Netlify API error "
                    f"{exc.response.status_code}: {body}"
                ),
            )

        except Exception as exc:
            return DeploymentResult(
                ok=False,
                provider="netlify",
                logs=f"Netlify request failed: {exc}",
            )

        return DeploymentResult(
            ok=True,
            provider="netlify",
            url=(
                data.get("deploy_ssl_url")
                or data.get("ssl_url")
                or data.get("url")
            ),
            deployment_id=data.get("id"),
            logs="Netlify deployment complete",
        )

    def _build_frontend(
        self,
        files: dict[str, str]
    ) -> dict[str, str]:

        # Extract only frontend source files
        frontend_files = {
            path.removeprefix("frontend/"): content
            for path, content in files.items()
            if path.startswith("frontend/")
            and not path.startswith("frontend/dist/")
        }

        if "package.json" not in frontend_files:
            raise RuntimeError(
                "Generated frontend is missing package.json."
            )

        with tempfile.TemporaryDirectory(
            prefix="autodev-netlify-"
        ) as temp:

            root = Path(temp)

            # Write generated frontend files
            for relative_path, content in frontend_files.items():

                target = root / relative_path

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                target.write_text(
                    content,
                    encoding="utf-8"
                )

            # Find npm on Windows/Linux
            npm = (
                shutil.which("npm.cmd")
                or shutil.which("npm")
            )

            if not npm:
                raise RuntimeError(
                    "npm was not found on PATH."
                )

            # Install dependencies
            install = subprocess.run(
                [
                    npm,
                    "install",
                    "--ignore-scripts",
                    "--no-audit",
                    "--no-fund",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=180,
            )

            if install.returncode != 0:

                output = (
                    install.stderr
                    or install.stdout
                )[-4000:]

                raise RuntimeError(
                    f"npm install failed:\n{output}"
                )

            # Build Vite frontend
            build = subprocess.run(
                [
                    npm,
                    "run",
                    "build"
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=180,
            )

            if build.returncode != 0:

                output = (
                    build.stderr
                    or build.stdout
                )[-4000:]

                raise RuntimeError(
                    f"npm run build failed:\n{output}"
                )

            dist = root / "dist"

            if not dist.exists():
                raise RuntimeError(
                    "Vite build completed without creating dist/."
                )

            # Read built files for Netlify ZIP
            static = {}

            for path in dist.rglob("*"):

                if path.is_file():

                    relative = path.relative_to(
                        dist
                    ).as_posix()

                    static[relative] = path.read_text(
                        encoding="utf-8"
                    )

            return static