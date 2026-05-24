---
description: "Plan or implement OpenHuman handoff work in the Cubecloud fork: copy docker-compose.openspace-openhuman.example.yml into OpenSpace, swap placeholder OpenSpace images, add the runtime-side OpenHuman JSON-RPC client, and wire core.ping, openhuman.inference_status, and openhuman.inference_prompt without exposing OpenHuman to the browser."
name: "Plan OpenHuman Handoff"
argument-hint: "Describe the OpenHuman slice, e.g. 'copy the compose example and add core.ping plus inference_status' or 'wire the first page-trigger inference_prompt path'"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use the **OpenHuman Handoff** agent (@openhuman-handoff) when the task is to wire OpenHuman behind OpenSpace as an internal worker rather than a public app or generic external-agent migration.

## Default Behavior

- Start in plan-only mode.
- Inventory the current OpenSpace runtime, compose, env, and smoke-test surfaces first.
- If the sibling OpenHuman repo exists locally, read `../openhuman/docs/OPENSPACE_OPENHUMAN_HANDOFF.md` and `../openhuman/docker-compose.openspace-openhuman.example.yml` before proposing edits.
- Report:
  - the smallest coordinated file set
  - which existing GHCR image references should replace the example placeholders
  - whether the runtime work belongs in a dedicated helper module versus an existing gateway
  - which request and response shapes are needed for `core.ping`, `openhuman.inference_status`, and `openhuman.inference_prompt`
  - what env vars and compose changes must move together
  - the narrowest validation plan and rollout risks
- Do not edit runtime, compose, env, or docs until the user explicitly approves implementation.

## Required Context

- [docker-compose.yml](../../docker-compose.yml)
- [docker-compose.release.yml](../../docker-compose.release.yml)
- [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml)
- [.env.example](../../.env.example)
- [smoke_test_mcp.py](../../smoke_test_mcp.py)
- [openspace/chat_thread_gateway.py](../../openspace/chat_thread_gateway.py)
- [openspace/external_agent_gateway.py](../../openspace/external_agent_gateway.py)
- [openspace/dashboard_server.py](../../openspace/dashboard_server.py)
- Sibling repo files if present locally: `../openhuman/docs/OPENSPACE_OPENHUMAN_HANDOFF.md`, `../openhuman/docker-compose.openspace-openhuman.example.yml`

## Planning Rules

- Treat this as a server-to-server JSON-RPC seam owned by the OpenSpace runtime on the existing `8788` path, not a frontend RPC integration.
- Preserve port ownership: `7788` dashboard, `8788` runtime, `5173` agents-monitor. OpenHuman should remain internal on the Docker network.
- Replace the example's placeholder OpenSpace images with the current GHCR image names already used by this fork. Do not invent a parallel naming scheme.
- Prefer one dedicated runtime helper near [openspace/chat_thread_gateway.py](../../openspace/chat_thread_gateway.py) over scattering ad hoc JSON-RPC calls across unrelated modules.
- Sequence the work: compose topology and env wiring, `core.ping`, `openhuman.inference_status`, first page-trigger `openhuman.inference_prompt`, then later chat if needed.
- Keep bearer tokens and OpenHuman auth inside runtime or container wiring only. Do not route `/rpc` through the browser or dashboard.
- Do not model the first slice as OpenClaw, Hermes, or standalone-app migration work unless inventory shows an unavoidable shared surface.
- If the local OpenHuman handoff files are missing, stop and ask for the contract instead of guessing JSON-RPC method names or result envelopes.