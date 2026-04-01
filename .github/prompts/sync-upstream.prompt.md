---
description: "Sync the Cubecloud fork with upstream HKUDS/OpenSpace — fetch, rebase our 5 Cubecloud commits onto upstream/main, resolve conflicts, run tests, and push."
name: "Sync with Upstream"
argument-hint: "Optional: target upstream commit or tag to sync to (default: upstream/main tip)"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use the **Upstream Sync** agent (@sync-upstream) to perform a full upstream sync for this repository.

## Parameters

- **Target** (optional): `${input:target:upstream/main tip}` — specific upstream commit SHA or tag to sync to, e.g. `2fb8024` or `upstream/main`.

## Context

This is the **Cubecloud fork** (`JZKK720/OpenSpace`) of `HKUDS/OpenSpace`.

Key facts the agent must know:
- We have **5 Cubecloud commits** on top of the fork base that must be preserved and re-tagged after rebase
- Push target is **`origin`** only — never `upstream`
- Force-push must use `--force-with-lease`
- The litellm `<1.82.7` pin from upstream is a **security fix** (PYSEC-2026-2) and must be preserved in `pyproject.toml` and `requirements.txt` after conflict resolution
- After rebase, re-apply `cubecloud-2026.03.29` and `cubecloud-2026.03.29.1` tags to their corresponding rebased commits

## Steps to Execute

1. Run pre-flight checks (clean working tree, remotes present)
2. Fetch `upstream` and `origin`
3. Show the user what upstream commits will be brought in and what Cubecloud commits will be replayed — **wait for confirmation**
4. Run `git rebase ${input:target:upstream/main}` and resolve all conflicts using the resolution rules in the agent definition
5. Run `python -m pytest tests/ -x -q` and `openspace-mcp --help` as smoke tests
6. Re-apply Cubecloud tags to the rebased commits
7. Push `main` and tags to `origin` with `--force-with-lease` — **wait for confirmation before pushing**

Report final status clearly: commits rebased, conflicts resolved, tests passed/failed, tags applied, push status.
