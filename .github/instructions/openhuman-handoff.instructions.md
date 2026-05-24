---
description: "Use when wiring OpenHuman behind OpenSpace, copying docker-compose.openspace-openhuman.example.yml, implementing runtime-side OpenHuman JSON-RPC calls, or handling core.ping, openhuman.inference_status, openhuman.inference_prompt, or OPENSPACE_OPENHUMAN_HANDOFF."
name: "OpenHuman Handoff Guidance"
---
# OpenHuman Handoff Guidance

- Treat the initial OpenHuman slice as a runtime-side server-to-server JSON-RPC integration, not a browser integration and not a standalone-app or external-agent registry migration.
- If the sibling repo exists locally at `../openhuman`, read `../openhuman/docs/OPENSPACE_OPENHUMAN_HANDOFF.md` and `../openhuman/docker-compose.openspace-openhuman.example.yml` before editing. If those files are unavailable, stop and ask for the contract instead of guessing request or response shapes.
- Preserve port ownership: `7788` is the OpenSpace gateway UI, `8788` is the OpenSpace runtime/API host port, and `5173` is the agents-monitor. OpenHuman stays an internal service reachable from the runtime at `http://openhuman:7788/rpc`.
- Do not call OpenHuman `/rpc` directly from frontend code. Keep the bearer token inside the OpenSpace runtime container only.
- When copying the compose topology, replace placeholder OpenSpace images with the actual GHCR images already used in [docker-compose.yml](../../docker-compose.yml), [docker-compose.release.yml](../../docker-compose.release.yml), and [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml). Keep [.env.example](../../.env.example), [README.md](../../README.md), and [INSTALL_FORK_WINDOWS.md](../../INSTALL_FORK_WINDOWS.md) aligned when introducing `OPENHUMAN_*` variables.
- For Python implementation, prefer a dedicated helper adjacent to [openspace/chat_thread_gateway.py](../../openspace/chat_thread_gateway.py) and reuse its request, auth, timeout, JSON decode, and error normalization patterns instead of scattering raw HTTP calls across routes or handlers.
- Implement in this order: `core.ping`, then `openhuman.inference_status`, then the first page-trigger path with `openhuman.inference_prompt`. Add `openhuman.inference_chat` only after the single-shot path is stable.
- Let OpenSpace own page or search context selection, prompt or message construction, token privacy, rendering, and tracing. Let OpenHuman own provider selection, inference execution, and inbound prompt-security enforcement.
- Do not model future direct OpenSpace index access as OpenClaw or Hermes bridging. That is a later backend decision, not part of the first handoff slice.
- Minimum validation after edits: `docker compose config`, a focused Python validation for the touched module or helper, and [smoke_test_mcp.py](../../smoke_test_mcp.py) extended or run at the narrowest level that exercises the new OpenHuman path.