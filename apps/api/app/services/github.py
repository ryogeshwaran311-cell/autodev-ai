from __future__ import annotations

import re

import httpx

from app.config import get_settings


class GitHubService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.github.com"

    def _headers(self):
        if not self.settings.github_token:
            raise RuntimeError("GITHUB_TOKEN is not configured")

        return {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def test_connection(self):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/user",
                headers=self._headers(),
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"GitHub authentication failed: "
                f"{response.status_code}"
            )

        data = response.json()

        return {
            "connected": True,
            "login": data.get("login"),
        }

    async def create_repository(
        self,
        name: str,
        description: str = "",
    ):
        if not self.settings.github_owner:
            raise RuntimeError("GITHUB_OWNER is not configured")

        safe_name = re.sub(
            r"[^a-zA-Z0-9._-]+",
            "-",
            name.strip(),
        ).strip("-")

        if not safe_name:
            safe_name = "autodev-generated-project"

        payload = {
            "name": safe_name,
            "description": description[:350],
            "private": False,
            "auto_init": True,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/user/repos",
                headers=self._headers(),
                json=payload,
            )

        if response.status_code != 201:
            raise RuntimeError(
                f"GitHub repository creation failed: "
                f"{response.status_code} "
                f"{response.text[:500]}"
            )

        data = response.json()

        return {
            "id": data["id"],
            "name": data["name"],
            "url": data["html_url"],
            "clone_url": data["clone_url"],
        }


github_service = GitHubService()