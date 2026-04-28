# Minimal Runtime Bundle

This deployment bundle is for running the published Cubecloud GHCR images without keeping the full source checkout in the same folder.

## Purpose

Use this when you want to reduce the amount of source code sitting in your working copy on a local machine while still keeping:

- `.env`
- external-agent registry config
- standalone-app registry config
- optional OpenSpace state under `.openspace`
- container logs under `logs`

## What This Bundle Assumes

This bundle expects the machine to be able to pull these published images from GHCR:

- `ghcr.io/jzkk720/openspace-cubecloud-dashboard:<tag>`
- `ghcr.io/jzkk720/openspace-agents-monitor:<tag>`
- `ghcr.io/jzkk720/openspace-runtime:<tag>`

By default the bundle uses `OPENSPACE_IMAGE_TAG=main`. Set `OPENSPACE_IMAGE_TAG=v0.5.0` in `.env` after that release tag is published if you want a pinned rollout.

## Important Security Limit

This reduces local source exposure by letting you move runtime files out of the full repo checkout, but it is not a complete code-protection boundary.

Anyone with local Docker access can still inspect local images and running containers.

If the machine itself is not trusted, use a stronger boundary such as:

- a separate deployment host
- a private image registry plus pull-only deployment
- OS account isolation and disk encryption

## Recommended Workflow

1. Export a runtime bundle with `scripts/prepare_runtime_bundle.ps1`.
2. Optionally pin `OPENSPACE_IMAGE_TAG` in the bundle `.env` or pass `-ImageTag` to the export script.
3. Run the bundle from a separate folder.
4. Archive or remove the full source checkout if you no longer want it on that machine.

## Running the Bundle

After exporting the bundle, go to the runtime folder and run:

```powershell
docker compose pull
docker compose up -d
```

## Updating the Runtime Bundle

After code or config changes in the main repo:

1. rerun `scripts/prepare_runtime_bundle.ps1`
2. pull the published images in the bundle folder
3. restart the runtime bundle with `docker compose up -d`

If you want to freeze a machine on a release tag, set `OPENSPACE_IMAGE_TAG` in the bundle `.env` before running the pull.

## Required Runtime Files

The bundle must contain:

- `.env`
- `docker-compose.yml`
- `openspace/config/external_agents.json`
- `openspace/config/standalone_apps.json`

Optional but commonly needed:

- `.openspace/`
- `logs/`