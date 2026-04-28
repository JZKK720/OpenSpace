---
description: "Use when editing Dockerfiles, Compose files, release workflows, deploy/local-runtime assets, or PowerShell release scripts for GHCR rollout, registry-first upgrades, or client distribution."
name: "Container Release Guidance"
applyTo: "docker-compose.yml,docker-compose.release.yml,deploy/local-runtime/**,Dockerfile.*,.github/workflows/*.yml,scripts/*.ps1"
---
# Container Release Guidance

- Treat `origin/main` as the Cubecloud deployment baseline. Review local drift against it before using `upstream/main` to justify packaging changes.
- Separate developer workflows from client-facing release workflows. Keep an explicit local build fallback for contributors, but prefer pull-first GHCR image references for release and upgrade paths.
- Do not add new `:local` image references to release-facing surfaces unless the task is explicitly local-only. If a release path still needs local tags, explain why in the change.
- Prefer immutable image tags such as commit SHAs or release tags, plus one stable channel tag for upgrade automation.
- When docs and prose differ from the checked-in runtime surfaces, trust [docker-compose.yml](../../docker-compose.yml), [docker-compose.release.yml](../../docker-compose.release.yml), [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml), and the PowerShell entry points in [scripts/](../../scripts/).
- Use the [GHCR Release agent](../agents/ghcr-release.agent.md) or the [Plan GHCR Release prompt](../prompts/ghcr-release.prompt.md) before broad release edits so Docker, scripts, and docs move together.