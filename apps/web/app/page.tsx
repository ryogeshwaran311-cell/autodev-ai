"use client";

import { useState } from "react";

export default function Home() {
  const [idea, setIdea] = useState("");
  const [generationMode, setGenerationMode] = useState("hybrid");
  const [generating, setGenerating] = useState(false);

async function generateProject() {
  if (!idea.trim()) {
    alert("Please describe your project idea first.");
    return;
  }

  setGenerating(true);

  try {
    // Step 1: Create project
    const createResponse = await fetch(
      "http://127.0.0.1:8000/api/projects",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: idea.trim().slice(0, 80),
          idea: idea.trim(),
          features: [],
          design_preferences: "",
          target_users: "",
          generation_mode: generationMode,
        }),
      }
    );

    const project = await createResponse.json();

    if (!createResponse.ok) {
      throw new Error(
        project.detail || project.message || "Project creation failed"
      );
    }

    // Step 2: Start AI generation
    const generateResponse = await fetch(
      `http://127.0.0.1:8000/api/projects/${project.id}/generate`,
      {
        method: "POST",
      }
    );

    const result = await generateResponse.json();

    if (!generateResponse.ok) {
      throw new Error(
        result.detail || result.message || "Generation request failed"
      );
    }

    alert(
      `Project created successfully!\n\nProject ID: ${project.id}\n\nAI generation has started.`
    );
  } catch (error) {
    console.error("Generation error:", error);

    alert(
      `Could not connect to the AutoDev AI backend.\n\n${
        error instanceof Error ? error.message : "Unknown error"
      }`
    );
  } finally {
    setGenerating(false);
  }
}

  return (
    <main className="min-h-screen bg-[#050816] text-white">
      {/* Header */}
      <header className="border-b border-white/10 bg-[#080b1a]/90">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-xl">
              ⚡
            </div>

            <div>
              <h1 className="text-lg font-bold">AutoDev AI</h1>

              <p className="text-xs text-gray-400">
                Autonomous Software Engineer
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="rounded-full border border-green-500/20 bg-green-500/10 px-3 py-1 text-xs text-green-400">
              ● System Online
            </span>

            <button className="rounded-lg border border-white/10 px-4 py-2 text-sm text-gray-300 transition hover:bg-white/5">
              Projects
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-6 pb-10 pt-16">
        <div className="max-w-3xl">
          <p className="mb-3 text-sm font-medium text-violet-400">
            AI-POWERED SOFTWARE DEVELOPMENT
          </p>

          <h2 className="text-4xl font-bold leading-tight md:text-6xl">
            Turn your idea into
            <span className="text-violet-400"> working software.</span>
          </h2>

          <p className="mt-5 max-w-2xl text-lg leading-8 text-gray-400">
            Describe what you want to build. AutoDev AI analyzes your
            requirements, creates the architecture, generates the code,
            tests the application, and prepares it for deployment.
          </p>
        </div>
      </section>

      {/* Project Generator */}
      <section className="mx-auto max-w-7xl px-6">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Generator Card */}
          <div className="rounded-2xl border border-white/10 bg-[#0b1022] p-6 lg:col-span-2">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold">
                  Create a new project
                </h3>

                <p className="mt-1 text-sm text-gray-500">
                  Describe your application in natural language.
                </p>
              </div>

              <span className="rounded-lg bg-violet-500/10 px-3 py-1 text-xs text-violet-400">
                AI Builder
              </span>
            </div>

            {/* Project Idea */}
            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder="Example: Build a student attendance management system with login, dashboard, attendance tracking, reports, and an admin panel..."
              className="h-52 w-full resize-none rounded-xl border border-white/10 bg-[#050816] p-5 text-sm text-white outline-none placeholder:text-gray-600 focus:border-violet-500"
            />

            {/* Generation Options */}
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <select
                value={generationMode}
                onChange={(e) => setGenerationMode(e.target.value)}
                className="rounded-xl border border-white/10 bg-[#050816] px-4 py-3 text-sm text-gray-300 outline-none focus:border-violet-500"
              >
                <option value="hybrid">Hybrid Generation</option>
                <option value="fully_ai">Fully AI Generated</option>
                <option value="template">Template Based</option>
              </select>

              {/* Generate Button */}
              <button
                onClick={generateProject}
                disabled={generating}
                className="flex-1 rounded-xl bg-violet-600 px-6 py-3 font-medium transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {generating ? "Generating..." : "Generate Project →"}
              </button>
            </div>
          </div>

          {/* AI Pipeline */}
          <div className="rounded-2xl border border-white/10 bg-[#0b1022] p-6">
            <h3 className="text-xl font-semibold">AI Pipeline</h3>

            <p className="mt-1 text-sm text-gray-500">
              Automated development workflow
            </p>

            <div className="mt-6 space-y-4">
              {[
                ["01", "Requirements Analysis"],
                ["02", "Architecture Planning"],
                ["03", "Code Generation"],
                ["04", "Testing & Repair"],
                ["05", "Validation"],
                ["06", "Deployment"],
              ].map(([number, name]) => (
                <div
                  key={number}
                  className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-3"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/10 text-xs text-violet-400">
                    {number}
                  </span>

                  <span className="text-sm text-gray-300">{name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="mx-auto max-w-7xl px-6 py-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Projects", "0"],
            ["Generating", "0"],
            ["Completed", "0"],
            ["Deployments", "0"],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-2xl border border-white/10 bg-[#0b1022] p-5"
            >
              <p className="text-sm text-gray-500">{label}</p>

              <p className="mt-2 text-3xl font-bold">{value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Recent Projects */}
      <section className="mx-auto max-w-7xl px-6 pb-16">
        <div className="rounded-2xl border border-white/10 bg-[#0b1022] p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold">Recent Projects</h3>

              <p className="mt-1 text-sm text-gray-500">
                Your generated applications will appear here.
              </p>
            </div>

            <button className="text-sm text-violet-400 transition hover:text-violet-300">
              View all →
            </button>
          </div>

          <div className="mt-8 flex min-h-32 items-center justify-center rounded-xl border border-dashed border-white/10">
            <div className="text-center">
              <div className="text-3xl">🚀</div>

              <p className="mt-2 text-sm text-gray-500">
                No projects generated yet
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-6 text-center text-xs text-gray-600">
        AutoDev AI • Autonomous Software Engineering Platform
      </footer>
    </main>
  );
}