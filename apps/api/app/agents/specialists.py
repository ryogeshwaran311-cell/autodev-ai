from __future__ import annotations

from abc import abstractmethod
import json
from html import escape

from app.agents.base import Agent
from app.schemas import AgentResult


# ============================================================
# File Safety
# ============================================================

def safe_files(data: dict) -> dict[str, str]:
    """
    Keep only safe relative text files.

    Reject:
    - absolute paths
    - parent traversal
    - non-string paths/content
    """
    out: dict[str, str] = {}

    for path, content in (data.get("files") or {}).items():
        if not isinstance(path, str):
            continue

        if not isinstance(content, str):
            continue

        normalized = path.replace("\\", "/")

        if normalized.startswith("/"):
            continue

        if normalized.startswith("./"):
            normalized = normalized[2:]

        if ".." in normalized.split("/"):
            continue

        out[normalized] = content

    return out


# ============================================================
# Requirements Agent
# ============================================================

class RequirementsAgent(Agent):
    name = "requirements"

    async def run(self, context: dict) -> AgentResult:
        idea = context["submission"]

        fallback = {
            "product_name": idea["title"],
            "summary": idea["idea"],
            "personas": [
                idea.get("target_users") or "General users"
            ],
            "functional_requirements": (
                idea.get("features")
                or [
                    "Responsive landing page",
                    "Authentication-ready structure",
                    "Dashboard",
                    "REST API",
                    "Persistent database",
                ]
            ),
            "non_functional_requirements": [
                "Responsive UI",
                "Secure defaults",
                "Fast load times",
                "Accessible components",
                "Observable deployments",
            ],
            "acceptance_criteria": [
                "Frontend builds without errors",
                "Backend health endpoint returns 200",
                "Generated tests pass",
            ],
        }

        data = await self.llm.json(
            "You are AutoDev AI's senior product analyst. "
            "Return only JSON. "
            "Convert vague product ideas into explicit, "
            "testable requirements. "
            "Never request secrets and never add illegal "
            "or dangerous behavior.",
            "Analyze this submission:\n"
            + json.dumps(idea, indent=2),
            fallback,
        )

        return AgentResult(
            agent=self.name,
            summary="Requirements normalized",
            data=data,
        )


# ============================================================
# Architecture Agent
# ============================================================

class ArchitectAgent(Agent):
    name = "architect"

    async def run(self, context: dict) -> AgentResult:
        req = context["requirements"]

        fallback = {
            "stack": {
                "frontend": "React + Vite",
                "backend": "FastAPI",
                "database": "Supabase PostgreSQL",
            },
            "frontend_routes": [
                "/",
                "/dashboard",
            ],
            "api_routes": [
                "/health",
                "/api/items",
            ],
            "entities": [
                {
                    "name": "items",
                    "fields": [
                        "id",
                        "title",
                        "created_at",
                    ],
                }
            ],
            "components": [
                "Navbar",
                "Hero",
                "Dashboard",
                "StatusCard",
            ],
            "security": [
                "RLS",
                "input validation",
                "CORS allowlist",
            ],
        }

        data = await self.llm.json(
            "You are a principal software architect. "
            "Return only JSON. "
            "Design a maintainable React/FastAPI/Supabase "
            "application. "
            "Prefer simple production-friendly architecture "
            "and explicit API contracts.",
            "Requirements:\n"
            + json.dumps(req, indent=2),
            fallback,
        )

        return AgentResult(
            agent=self.name,
            summary="Architecture created",
            data=data,
        )


# ============================================================
# Database Agent
# ============================================================

class DatabaseAgent(Agent):
    name = "database"

    async def run(self, context: dict) -> AgentResult:
        arch = context["architecture"]

        fallback_sql = """create extension if not exists pgcrypto;

create table if not exists public.items (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    created_at timestamptz not null default now()
);

alter table public.items enable row level security;

create policy "authenticated users can read items"
on public.items
for select
to authenticated
using (true);
"""

        fallback = {
            "files": {
                "supabase/migrations/001_app.sql": fallback_sql
            }
        }

        data = await self.llm.json(
            "You are a PostgreSQL/Supabase database engineer. "
            "Return JSON with a `files` object. "
            "Generate idempotent SQL migrations, constraints, "
            "indexes, RLS, and safe policies. "
            "Never disable RLS for user-owned data. "
            "Do not include real credentials.",
            "Architecture:\n"
            + json.dumps(arch, indent=2),
            fallback,
        )

        files = safe_files(data)

        return AgentResult(
            agent=self.name,
            summary="Database schema generated",
            data=data,
            files=files,
        )


# ============================================================
# Frontend Agent
# ============================================================

class FrontendAgent(Agent):
    name = "frontend"

    async def run(self, context: dict) -> AgentResult:
        req = context["requirements"]
        arch = context["architecture"]

        product_name = escape(
            str(req.get("product_name", "Your Product"))
        )

        summary = escape(
            str(
                req.get(
                    "summary",
                    "Generated application",
                )
            )[:600]
        )

        package_json = {
            "name": "autodev-generated-frontend",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "test": "vitest run",
            },
            "dependencies": {
                "react": "^19.1.0",
                "react-dom": "^19.1.0",
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^5.0.0",
                "vite": "^7.0.0",
                "typescript": "^5.8.0",
                "vitest": "^3.2.0",
            },
        }

        fallback = {
            "files": {
                "frontend/package.json": json.dumps(
                    package_json,
                    indent=2,
                ),

                "frontend/index.html": f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    />
    <title>{product_name}</title>
</head>
<body>
    <div id="root"></div>
    <script
        type="module"
        src="/src/main.jsx"
    ></script>
</body>
</html>
""",

                "frontend/src/main.jsx": f"""import React from "react";
import {{ createRoot }} from "react-dom/client";
import "./style.css";

function App() {{
    return (
        <main className="shell">
            <nav>
                <b>{product_name}</b>
                <span>AutoDev AI</span>
            </nav>

            <section className="hero">
                <p className="badge">
                    AI-generated application
                </p>

                <h1>{product_name}</h1>

                <p>{summary}</p>

                <button   
                    type="button"
                    onclick={{()=> alert("Application started")}}
                >
                    Get Started
                </button>
                
            </section>
        </main>
    );
}}

const root = document.getElementById("root");

if (root) {{
    createRoot(root).render(<App />);
}}
""",

                "frontend/src/style.css": """
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Inter, system-ui, sans-serif;
    background: #07111f;
    color: #eef6ff;
}

.shell {
    min-height: 100vh;
    background:
        radial-gradient(
            circle at 80% 10%,
            #16365e55,
            transparent 35%
        );
}

nav {
    display: flex;
    justify-content: space-between;
    padding: 24px 7%;
    border-bottom: 1px solid #ffffff16;
}

.hero {
    max-width: 900px;
    padding: 12vh 7%;
}

.badge {
    display: inline-block;
    padding: 7px 12px;
    border: 1px solid #ffffff2a;
    border-radius: 999px;
}

.hero h1 {
    font-size: clamp(3rem, 9vw, 7rem);
    line-height: 0.95;
    margin: 24px 0;
}

.hero p {
    font-size: 1.1rem;
    line-height: 1.7;
    color: #bed2e7;
}

button {
    border: 0;
    border-radius: 12px;
    padding: 14px 20px;
    font-weight: 700;
    cursor: pointer;
}
""",
            }
        }

        data = await self.llm.json(
            "You are an expert React UI engineer. "
            "Return JSON with a `files` object only plus "
            "optional metadata. "
            "Generate a complete Vite React app. "
            "Use accessible semantic HTML, responsive CSS, "
            "and no external secrets. "
            "All imports must resolve. "
            "Prefer plain React/CSS unless a dependency "
            "is explicitly included in package.json.",
            "Requirements:\n"
            + json.dumps(req, indent=2)
            + "\nArchitecture:\n"
            + json.dumps(arch, indent=2),
            fallback,
        )

        files = safe_files(data)

        return AgentResult(
            agent=self.name,
            summary="React application generated",
            data=data,
            files=files,
        )


# ============================================================
# Backend Agent
# ============================================================

class BackendAgent(Agent):
    name = "backend"

    async def run(self, context: dict) -> AgentResult:
        arch = context["architecture"]

        fallback = {
            "files": {
                "backend/requirements.txt": (
                    "fastapi>=0.116,<1\n"
                    "uvicorn>=0.35,<1\n"
                ),

                "backend/app/main.py": """from fastapi import FastAPI

app = FastAPI(
    title="Generated AutoDev API"
)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/items")
def items():
    return {"items": []}
""",

                "backend/vercel.json": json.dumps(
                    {
                        "$schema": (
                            "https://openapi.vercel.sh/"
                            "vercel.json"
                        ),
                        "rewrites": [
                            {
                                "source": "/(.*)",
                                "destination": "/app/main.py",
                            }
                        ],
                    },
                    indent=2,
                ),
            }
        }

        data = await self.llm.json(
            "You are an expert Python/FastAPI backend "
            "engineer. "
            "Return JSON with a `files` object. "
            "Generate a complete API with Pydantic validation, "
            "health endpoint, safe error handling, "
            "environment-variable configuration, and "
            "Supabase integration where required. "
            "Never hard-code secrets.",
            "Architecture:\n"
            + json.dumps(arch, indent=2),
            fallback,
        )

        files = safe_files(data)

        return AgentResult(
            agent=self.name,
            summary="FastAPI backend generated",
            data=data,
            files=files,
        )


# ============================================================
# QA Agent
# ============================================================

class QAAgent(Agent):
    name = "qa"

    async def run(self, context: dict) -> AgentResult:
        files = context["files"]
        manifest = list(files.keys())

        has_frontend = any(
            path.startswith("frontend/")
            for path in manifest
        )

        has_package = (
            "frontend/package.json"
            in manifest
        )

        has_backend = any(
            path.startswith("backend/")
            for path in manifest
        )

        has_python = any(
            path.endswith(".py")
            and path.startswith("backend/")
            for path in manifest
        )

        # ----------------------------------------------------
        # Safe deterministic fallback commands
        #
        # IMPORTANT:
        # Never use:
        #   cd ...
        #   &&
        #   ||
        #   shell pipes
        #
        # npm --prefix allows us to target frontend safely.
        # ----------------------------------------------------

        test_commands: list[str] = []

        if has_frontend and has_package:
            test_commands.append(
                "npm install --prefix frontend"
            )
            test_commands.append(
                "npm run build --prefix frontend"
            )

        if has_backend and has_python:
            test_commands.append(
                "python -m compileall backend/app"
            )

        fallback = {
            "test_commands": test_commands,
            "acceptance_checks": [
                "Frontend build passes"
                if has_frontend
                else "No frontend build required",

                "Python source compiles"
                if has_backend
                else "No backend compilation required",
            ],
        }

        data = await self.llm.json(
            "You are a QA automation lead. "
            "Return only JSON. "
            "Given a generated repository manifest, define "
            "deterministic build/test commands. "

            "IMPORTANT COMMAND SAFETY RULES: "
            "Never use `cd`. "
            "Never use `&&`, `||`, `;`, shell pipes, backticks, "
            "command substitution, sudo, curl-pipe-shell, "
            "wget-pipe-shell, destructive commands, or secrets. "

            "For frontend commands use "
            "`npm --prefix frontend ...`. "

            "For backend Python validation use direct commands "
            "such as `python -m compileall backend/app`. "

            "Return standalone commands only.",
            "Files:\n"
            + json.dumps(manifest, indent=2),
            fallback,
        )

        # ----------------------------------------------------
        # Defense-in-depth:
        # Gemini may ignore instructions.
        # Sanitize its output before BuildRunner receives it.
        # ----------------------------------------------------

        raw_commands = data.get("test_commands") or []

        safe_commands: list[str] = []

        for command in raw_commands:
            if not isinstance(command, str):
                continue

            command = " ".join(command.strip().split())

            # Reject shell control operators.
            dangerous_tokens = [
                ";",
                "&&",
                "||",
                "|",
                "`",
                "$(",
                "sudo ",
                "rm -rf",
                "curl ",
                "wget ",
            ]

            if any(
                token in command
                for token in dangerous_tokens
            ):
                continue

            # Never allow directory-changing commands.
            if command.startswith("cd "):
                continue

            # Only retain known safe command families.
            allowed = (
                command.startswith("npm install"),
                command.startswith("npm ci"),
                command.startswith("npm run build"),
                command.startswith("npm test"),
                command.startswith("python -m compileall"),
                command.startswith("python -m pytest"),
                command.startswith("pip install"),
            )

            if not any(allowed):
                continue

            safe_commands.append(command)

        # If Gemini returned nothing safe, use our deterministic
        # fallback.
        if not safe_commands:
            safe_commands = test_commands

        data["test_commands"] = safe_commands

        return AgentResult(
            agent=self.name,
            summary="QA plan generated",
            data=data,
        )


# ============================================================
# Security Agent
# ============================================================

class SecurityAgent(Agent):
    name = "security"

    async def run(self, context: dict) -> AgentResult:
        files = context["files"]

        findings = []

        banned = [
            (
                "curl | sh",
                "Remote shell pipe",
            ),
            (
                "wget | sh",
                "Remote shell pipe",
            ),
            (
                "rm -rf /",
                "Destructive root deletion",
            ),
            (
                "subprocess.Popen",
                "Unreviewed process execution",
            ),
            (
                "os.system(",
                "Unreviewed shell execution",
            ),
        ]

        text = "\n".join(
            files.values()
        ).lower()

        for needle, label in banned:
            if needle.lower() in text:
                findings.append(
                    {
                        "severity": "high",
                        "rule": label,
                        "pattern": needle,
                    }
                )

        data = {
            "passed": not findings,
            "findings": findings,
        }

        return AgentResult(
            agent=self.name,
            summary="Security scan complete",
            data=data,
        )


# ============================================================
# DevOps Agent
# ============================================================

class DevOpsAgent(Agent):
    name = "devops"

    async def run(self, context: dict) -> AgentResult:
        fallback = {
            "frontend": {
                "provider": "netlify",
                "build": "npm run build",
                "publish": "frontend/dist",
            },
            "backend": {
                "provider": "vercel",
                "root": "backend",
            },
            "rollback": (
                "Retain previous deployment ID and "
                "promote/redeploy it on rollback."
            ),
        }

        data = await self.llm.json(
            "You are a DevOps/SRE engineer. "
            "Return only JSON. "
            "Create a preview-first deployment plan for "
            "Netlify frontend, Vercel FastAPI backend, "
            "Supabase migrations, observability, "
            "environment isolation, rollback, "
            "and least privilege.",
            "QA:\n"
            + json.dumps(
                context["qa"],
                indent=2,
            ),
            fallback,
        )

        return AgentResult(
            agent=self.name,
            summary="Deployment plan generated",
            data=data,
        )


# ============================================================
# Refinement Agent
# ============================================================

class RefinementAgent(Agent):
    name = "refinement"

    async def run(self, context: dict) -> AgentResult:
        request = context["request"]

        fallback = {
            "scopes": ["frontend"],
            "reason": "UI refinement",
        }

        data = await self.llm.json(
            "Classify a software change request. "
            "Return JSON: "
            "{scopes: [...], reason: string}. "
            "Allowed scopes: "
            "requirements,database,frontend,backend,"
            "tests,deployment. "
            "Select only scopes that truly need regeneration.",
            request,
            fallback,
        )

        return AgentResult(
            agent=self.name,
            summary="Refinement scope classified",
            data=data,
        )