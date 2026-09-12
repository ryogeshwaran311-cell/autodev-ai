from __future__ import annotations
from pathlib import Path
import tempfile
from app.schemas import BuildResult
from app.config import get_settings

SAFE_COMMAND_PREFIXES = (
    "npm install", "npm ci", "npm run build", "npm test",
    "python -m compileall", "python -m pytest", "pip install"
)

def validate_command(command: str):
    c = " ".join(command.strip().split())
    if any(x in c for x in [";", "&&", "||", "|", "`", "$(", "sudo ", "rm -rf"]):
        raise ValueError(f"Unsafe test command rejected: {command}")
    if not c.startswith(SAFE_COMMAND_PREFIXES):
        raise ValueError(f"Command not allowlisted: {command}")

class BuildRunner:
    async def validate(self, files: dict[str, str], commands: list[str]) -> BuildResult:
        for path in files:
            p = Path(path)
            if p.is_absolute() or ".." in p.parts:
                return BuildResult(ok=False, logs=f"Unsafe artifact path: {path}")

        for cmd in commands:
            validate_command(cmd)

        settings = get_settings()
        if settings.app_env == "production" and settings.vercel_oidc_token:
            return await self._vercel_sandbox(files, commands)

        # Local/demo structural validation. We intentionally do not execute
        # AI-generated shell commands on the host machine.
        required = ["frontend/package.json", "backend/app/main.py"]
        missing = [p for p in required if p not in files]
        if missing:
            return BuildResult(ok=False, logs=f"Missing required generated files: {missing}")
        return BuildResult(
            ok=True,
            logs="Structural validation passed. Production mode can execute builds in Vercel Sandbox."
        )

    async def _vercel_sandbox(self, files: dict[str, str], commands: list[str]) -> BuildResult:
        """
        Vercel Sandbox Python SDK integration.
        The exact write-file surface can evolve; this method uses a generated
        bootstrap script so only one trusted Python command is invoked.
        """
        import json, base64
        from vercel.sandbox import Sandbox

        payload = {
            path: base64.b64encode(content.encode()).decode()
            for path, content in files.items()
        }
        bootstrap = f"""
import base64, json
from pathlib import Path
files = json.loads({json.dumps(json.dumps(payload))})
for path, content in files.items():
    p = Path('/vercel/sandbox/work') / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(base64.b64decode(content))
print('wrote', len(files), 'files')
"""
        logs = []
        with Sandbox.create(runtime="python3.13") as sandbox:
            write = sandbox.run_command("python", ["-c", bootstrap])
            logs.append(str(write.stdout()))
            for command in commands:
                # Allowlisted and parsed without invoking a shell.
                parts = command.split()
                proc = sandbox.run_command(parts[0], parts[1:])
                logs.append(f"$ {command}\n{proc.stdout()}\n{proc.stderr()}")
                exit_code = getattr(proc, "exit_code", 0)
                if callable(exit_code):
                    exit_code = exit_code()
                if exit_code not in (0, None):
                    return BuildResult(ok=False, logs="\n".join(logs))
        return BuildResult(ok=True, logs="\n".join(logs))
