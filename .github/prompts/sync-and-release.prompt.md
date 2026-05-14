---
description: "Combined upstream sync and GHCR release: fetch upstream commits, merge or rebase onto fork/main, validate, push to origin (which auto-publishes main-channel images), and optionally tag a versioned release."
name: "Sync Upstream and Release"
argument-hint: "Optional: upstream ref to sync to (default: upstream/main) and/or release tag (e.g. v1.2.3)"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use this prompt when upstream (`HKUDS/OpenSpace`) has commits that the Cubecloud fork needs to adopt **and** you want the updated images published to GHCR in the same session.

## Parameters

- **Target** (optional): `${input:target:upstream/main}` — upstream ref to sync to.
- **Release tag** (optional): `${input:tag:}` — if provided, push a `vX.Y.Z` tag after sync to trigger a versioned GHCR release in addition to the `main`-channel publish.

## How the GHCR workflow fires

The checked-in `ghcr-release.yml` workflow triggers automatically on:

- **push to `main`** → publishes `main`-channel images (`openspace-runtime:main`, `openspace-agents-monitor:main`, `openspace-cubecloud-dashboard:main`) and immutable `sha-<shortsha>` tags
- **push of a `v*` tag** → additionally publishes `vX.Y.Z` tagged images and creates a GitHub Release

No `workflow_dispatch` is needed after a normal sync push. A manual trigger is only required if you need to re-publish without a new commit.

## Step 1 — Sync review (delegate to Upstream Sync agent)

Run the full review from the [Sync with Upstream prompt](./sync-upstream.prompt.md) first, producing:

1. Local vs `origin/main` classification (`in-sync`, `behind`, `ahead`, `diverged`)
2. `origin/main` vs `upstream/TARGET` divergence summary with commit list
3. Recommended strategy: `no update`, `cherry-pick`, or `rebase`
4. Conflict hotspots and whether any require escalation before proceeding
5. Whether the upstream delta includes Dockerfile, `pyproject.toml`, `requirements*.txt`, or security pin changes that affect GHCR image content

**Stop here and present the report.** Do not proceed to execution until the user approves a strategy.

## Step 2 — Sync execution (only after confirmation)

Follow the execution rules from the [Upstream Sync agent](../agents/sync-upstream.agent.md):

- Require a clean working tree before any write
- Perform cherry-pick or rebase as approved
- Resolve conflicts using the hotspot rules (upstream wins for security/bug patches; fork wins for fork-only product surfaces)
- Always verify the `litellm<1.82.7` pin in `pyproject.toml` **and** `requirements.txt` after conflict resolution
- Remap `cubecloud-*` tags if history changed; show old → new SHA mapping for confirmation

## Step 3 — Build validation

Run the minimum validation set for the surfaces touched by the sync. Always include:

```powershell
pip install -e ".[windows]"
openspace-mcp --help
python -m json.tool openspace/config/external_agents.json
python -m json.tool openspace/config/standalone_apps.json
python smoke_test_mcp.py --level 1
```

Add when `frontend/` or `showcase/` changed:

```powershell
Set-Location frontend; npm install; npm run build
Set-Location showcase/my-daily-monitor; npm install; npm run build
```

Add when `docker-compose.yml`, `Dockerfile.*`, or `.env` wiring changed:

```powershell
docker compose config
```

## Step 4 — Push to origin/main (triggers GHCR main-channel publish)

After validation passes:

```powershell
git push origin main --force-with-lease
git push origin --tags --force-with-lease   # only if cubecloud-* tags were remapped
```

State clearly that this push will trigger `ghcr-release.yml` and publish `main`-channel images. The user does not need to dispatch the workflow separately.

## Step 5 — Versioned release tag (optional)

If the user provided a release tag or requests a versioned release:

```powershell
git tag vX.Y.Z
git push origin vX.Y.Z
```

This triggers the `release` job in `ghcr-release.yml`, which:
- publishes `vX.Y.Z` tagged images for all three services
- creates a GitHub Release with auto-generated notes

Confirm the tag name with the user before pushing. Suggest following the existing `vMAJOR.MINOR.PATCH` convention.

## Step 6 — Post-push confirmation

After push, verify the workflow started on GitHub Actions (if the user has browser or API access). Then optionally confirm the running stack reflects the new images:

```powershell
docker compose pull
docker compose up -d
Invoke-WebRequest http://127.0.0.1:7788/api/v1/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:7788/api/v1/external-agents -UseBasicParsing
```

## Constraints

- **NEVER** push to `upstream`. All pushes target `origin` only.
- **NEVER** force-push without `--force-with-lease`.
- **NEVER** delete or squash `cubecloud-*` tags without showing the old → new SHA mapping.
- **NEVER** proceed past Step 1 without explicit user confirmation of the sync strategy.
- **NEVER** push a version tag that conflicts with an existing published release without raising a warning.

## Output Format

Return in this order:
1. Sync review report (Step 1)
2. Conflict resolution summary (Step 2, if executed)
3. Validation results (Step 3)
4. Push confirmation and expected GHCR jobs (Step 4)
5. Release tag confirmation (Step 5, if applicable)
6. Post-push stack status (Step 6, if applicable)
