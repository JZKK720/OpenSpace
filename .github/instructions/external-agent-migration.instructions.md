---
description: "Use when editing external agent registry, env wiring, Compose, gateway adapters, or docs for delegated runtime swaps such as Nanobot to OpenClaw, protocol changes, or port moves."
name: "External Agent Migration Guidance"
applyTo: "openspace/config/external_agents.json,openspace/config/external_agents.contract.md,openspace/dashboard_server.py,openspace/external_agent_gateway.py,openspace/external_agents.py,openspace/nanobot_gateway.py,docker-compose.yml,docker-compose.release.yml,deploy/local-runtime/docker-compose.yml,.env,.env.example,INSTALL_FORK_WINDOWS.md,README.md,smoke_test_mcp.py"
---
# External Agent Migration Guidance

- Treat runtime swaps as coordinated migrations across registry, env vars, Compose, dashboard wiring, docs, and smoke tests; do not land one slice in isolation.
- Start from [openspace/config/external_agents.contract.md](../../openspace/config/external_agents.contract.md) and [openspace/config/external_agents.json](../../openspace/config/external_agents.json); keep `id`, `protocol`, URL env names, capabilities, and linked MCP servers coherent.
- For OpenClaw integration, check [openspace/host_skills/README.md](../../openspace/host_skills/README.md) before reusing Nanobot assumptions. OpenClaw MCP setup uses `openclaw mcp set` or mcporter and may need a different contract shape than `nanobot-mcp`.
- If the change also moves ports, update `.env*`, both Compose paths, and install docs together. Avoid collisions with `OPENSPACE_RUNTIME_PORT` default `8788`, dashboard `7788`, and agents-monitor `5173`.
- Keep GHCR release surfaces aligned when Compose or env defaults change; review [docker-compose.release.yml](../../docker-compose.release.yml), [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml), and [INSTALL_FORK_WINDOWS.md](../../INSTALL_FORK_WINDOWS.md) together.
- Prefer plan-first review when replacing a runtime entirely. Inventory stale env names, gateway modules, docs, and smoke coverage before deleting adapters or changing protocol labels.
- If a runtime is removed from the dashboard surface, also check `openspace/dashboard_server.py`, `openspace/external_agents.py`, `openspace/external_agent_gateway.py`, and `smoke_test_mcp.py`.