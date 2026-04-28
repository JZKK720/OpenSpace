---
description: "Plan or implement a GHCR-based image workflow for the Cubecloud fork: review the current checkout against origin/main, inspect Docker and install surfaces, compare upstream build changes when needed, propose ghcr.io image names and tags, and optionally scaffold pull-first release automation after confirmation."
name: "Plan GHCR Release"
argument-hint: "Optional: release scope, target tag, or specific services to publish"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use the **GHCR Release** agent (@ghcr-release) when the goal is to stop rebuilding Docker images on every client machine and move the Cubecloud fork toward pull-first upgrades.

## Parameters

- **Scope** (optional): `${input:scope:all compose services}` — which services should publish to GHCR.
- **Target** (optional): `${input:target:origin/main}` — the fork ref that should define the release baseline.

## Default Behavior

- Start in plan-only mode.
- Review the current checkout against `origin/main` first, then inspect upstream build-related changes only if they affect packaging, dependency safety, or Docker release decisions.
- Report:
  - local drift from the fork deployment baseline
  - the current Docker, Compose, bundle, and install surfaces that still require local builds
  - a concrete GHCR image naming and tag plan
  - the repo changes needed to let clients pull images instead of rebuilding them locally
  - the validation and rollout steps, including any secrets or package-visibility blockers
- Do not edit Dockerfiles, Compose files, scripts, workflows, or docs until the user explicitly asks for implementation.

## Required Planning Rules

- Keep `origin/main` as the operational baseline for Cubecloud builds.
- Never push to `upstream`; package publishing belongs under the fork owner namespace.
- Prefer immutable image tags plus a stable channel tag.
- Keep a local development fallback instead of forcing all contributors onto GHCR pulls.
- When docs disagree with manifests or scripts, trust `docker-compose.yml`, `deploy/local-runtime/docker-compose.yml`, `Dockerfile.*`, and `scripts/*.ps1`.

## Suggested Implementation Scope

If the user approves implementation, the agent may update:

- `.github/workflows/` for GHCR publishing automation
- `docker-compose.yml` and `deploy/local-runtime/docker-compose.yml`
- `scripts/docker-up.ps1`, `scripts/install.ps1`, `scripts/prepare_runtime_bundle.ps1`
- `README.md`, `INSTALL_FORK_WINDOWS.md`, `deploy/local-runtime/README.md`

The final report should clearly separate the current baseline, the GHCR design, the required file changes, the validation plan, and any blockers.