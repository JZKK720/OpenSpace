---
description: "Review whether the current checkout is behind fork/main, whether the Cubecloud fork is behind upstream HKUDS/OpenSpace, decide whether the fork should update now, draft a cherry-pick or rebase plan, produce a local build and validation plan, and optionally execute the sync after confirmation."
name: "Sync with Upstream"
argument-hint: "Optional: target upstream commit or tag to sync to (default: upstream/main tip)"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use the **Upstream Sync** agent (@sync-upstream) to compare this fork against upstream before any history-changing action.

## Parameters

- **Target** (optional): `${input:target:upstream/main}` — specific upstream commit SHA, tag, or ref to compare against.

## Default Behavior

- Start in review-only mode.
- Fetch `upstream` and `origin`, then report:
  - local-only commits and remote-only commits relative to `origin/main`, so the user can see whether the checkout already drifted from the fork baseline used by Cubecloud builds
  - upstream-only commits relative to `main`
  - fork-only commits and all `cubecloud-*` tags that must be preserved
  - the recommended sync strategy: `no update`, cherry-pick selected upstream commits, or rebase the fork onto the target
  - likely conflict hotspots, config or API drift that must be checked, whether Docker/build changes should also trigger a GHCR release plan, and a layer-by-layer local build and validation plan
- Do not rebase, cherry-pick, retag, or push until the user explicitly asks for execution.
- If the user also asks whether published GHCR images are behind the fork baseline, finish the git divergence report first and then hand the registry portion to the [Plan GHCR Release](./ghcr-release.prompt.md) workflow instead of guessing from git state alone.

## Recommendation Rules

- Recommend `no update yet` when the upstream delta is docs-only, low value for this fork, or concentrated in fork-only product surfaces without a matching bugfix or security reason.
- Recommend `cherry-pick` when the upstream delta is small, high-value, and isolated away from the main divergence hotspots.
- Recommend `rebase` when the user wants a refreshed upstream baseline, the replay set is broad, or security and dependency fixes touch multiple shared layers.
- Escalate instead of guessing when both sides changed `openspace/config/external_agents.json`, `openspace/config/standalone_apps.json`, `docker-compose.yml`, dashboard handoff code, or branding-sensitive frontend text in the same slice.

## Context

This is the **Cubecloud fork** (`JZKK720/OpenSpace`) of `HKUDS/OpenSpace`.

Key facts the agent must know:
- This fork is intentionally diverged for Cubecloud dashboard, showcase, and Windows and local-runtime support
- `origin/main` is the deployment baseline for Cubecloud builds, so review local drift against it before drawing upstream conclusions
- Push target is **`origin`** only — never `upstream`
- Force-push must use `--force-with-lease`
- The litellm `<1.82.7` pin from upstream is a **security fix** (PYSEC-2026-2) and must be preserved in `pyproject.toml` and `requirements.txt` after conflict resolution
- Preserve all `cubecloud-*` tags if history changes
- Discover current fork-only commits dynamically; do not assume a fixed commit count
- When docs disagree with checked-in manifests or scripts, trust `pyproject.toml`, `frontend/package.json`, `showcase/my-daily-monitor/package.json`, `docker-compose.yml`, and `scripts/*.ps1`

## Validation Plan

The report must include the relevant commands for the touched surfaces:

- Python and CLI: `pip install -e ".[windows]"`, `openspace-mcp --help`
- Python checks when relevant: `pytest`, `black openspace/`, `flake8 openspace/`, `mypy openspace/`
- Config integrity: `python -m json.tool openspace/config/external_agents.json`, `python -m json.tool openspace/config/standalone_apps.json`
- Security drift: confirm `litellm<1.82.7` remains present in both `pyproject.toml` and `requirements.txt`
- Dashboard frontend: `Set-Location frontend; npm install; npm run build`
- Showcase app: `Set-Location showcase/my-daily-monitor; npm install; npm run build`
- Docker: `docker compose config` and, if needed, `docker compose up -d --build`
- Dashboard API when the stack is running: `Invoke-WebRequest http://127.0.0.1:7788/api/v1/health -UseBasicParsing`, `Invoke-WebRequest http://127.0.0.1:7788/api/v1/external-agents -UseBasicParsing`, `Invoke-WebRequest http://127.0.0.1:7788/api/v1/standalone-apps -UseBasicParsing`
- Smoke: `python smoke_test_mcp.py --level 1`, plus level 2 only when required secrets are available

## Execution Mode

If the user approves actual sync work, continue with confirmation gates for:

1. clean working tree checks before any write operation
2. fetch and compare
3. cherry-pick or rebase execution
4. conflict resolution and validation
5. `cubecloud-*` tag remapping if history changed
6. push to `origin` only, using `--force-with-lease` when required

If the safest recommendation is `no update`, stop after the report and explain what would need to change before a sync becomes worthwhile.

Report final status clearly: divergence summary, recommended sync path, conflict risks, validation plan, and execution status if any changes were made.
