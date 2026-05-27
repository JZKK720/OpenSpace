---
description: "Plan or review how the ECC fork could integrate with the Cubecloud OpenSpace fork as a delegated runtime, shared MCP or tool surface, standalone utility app, workflow source, or orchestration sidecar without drifting into a brittle raw-code merge."
name: "Plan ECC Integration"
argument-hint: "Describe the ECC idea, e.g. 'brainstorm ECC as a delegated runtime with dashboard utility surfaces'"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use the **ECC Integration** agent (@ecc-integration) when the task is to review, plan, or cautiously prototype how the ECC fork could plug into OpenSpace.

## Default Behavior

- Start in plan-only mode.
- Review OpenSpace's existing external-agent, standalone-app, dashboard, and host-skill surfaces first.
- Treat ECC as a raw harness and operator system, not a library to import wholesale.
- Report:
  - the smallest viable integration shape
  - whether the requested outcome fits a delegated runtime, linked MCP server, standalone app, curated workflow or skill import, or thin sidecar adapter
  - which pieces can stay config-driven versus which require new Python or frontend glue
  - what utility surfaces would actually improve the OpenSpace experience
  - the validation and rollout plan
  - what not to merge or copy
- Do not edit runtime configs, Compose, or dashboard code until the user explicitly approves implementation.

## Required Context

For this repo, the sources of truth are:

- [openspace/config/external_agents.contract.md](../../openspace/config/external_agents.contract.md)
- [openspace/config/external_agents.json](../../openspace/config/external_agents.json)
- [openspace/config/standalone_apps.json](../../openspace/config/standalone_apps.json)
- [openspace/external_agent_gateway.py](../../openspace/external_agent_gateway.py)
- [openspace/external_agents.py](../../openspace/external_agents.py)
- [openspace/standalone_apps.py](../../openspace/standalone_apps.py)
- [openspace/openhuman_gateway.py](../../openspace/openhuman_gateway.py)
- [openspace/openhuman_rpc_gateway.py](../../openspace/openhuman_rpc_gateway.py)
- [openspace/mcp_server.py](../../openspace/mcp_server.py)
- [openspace/dashboard_server.py](../../openspace/dashboard_server.py)
- [openspace/host_skills/README.md](../../openspace/host_skills/README.md)
- [docker-compose.yml](../../docker-compose.yml)
- [docker-compose.release.yml](../../docker-compose.release.yml)
- [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml)
- [README.md](../../README.md)
- [INSTALL_FORK_WINDOWS.md](../../INSTALL_FORK_WINDOWS.md)

For ECC, inspect the public repo surfaces that explain its runtime shape before proposing any integration:

- `README.md`
- `AGENTS.md`
- `package.json`
- `pyproject.toml`
- `agent.yaml`
- `ecc_dashboard.py`
- `commands/`, `skills/`, `mcp-configs/`, `hooks/`, and `ecc2/`

## Planning Rules

- Prefer boundary integrations over raw code merges. First try:
  - external delegated runtime
  - linked MCP server or tool bridge
  - standalone app card
  - curated workflow or skill import
  - thin sidecar adapter
- Only recommend direct code import when the target is a narrow self-contained utility with a stable CLI or HTTP contract and a clear owner.
- Keep OpenSpace's source of truth in its existing registries and dashboard APIs. Avoid duplicating ECC catalogs inside OpenSpace unless the user explicitly wants mirroring.
- If the goal is "more orchestration with OpenSpace surface," bias toward OpenSpace as the control plane and ECC as an attached operator subsystem, not a second competing control plane.
- Separate utility-surface ideas into:
  - dashboard browse or launch surfaces
  - delegated task handoff surfaces
  - MCP tool surfaces
  - workflow or skill import surfaces
  - status or session summary surfaces
- If ECC functionality maps cleanly onto `http-json`, `openai-compat`, `chat-thread`, or MCP, prefer the existing adapter surfaces over new protocol code.
- Use OpenHuman as the reference for a deeper handoff only when a protocol-specific gateway is actually justified.
- Call out when the idea is really a product or packaging question rather than a code integration question.

## Output Format

Return these sections in order:

1. OpenSpace surfaces that matter
2. ECC surfaces worth integrating
3. Feasible integration patterns
4. Recommended phased approach
5. Utility surface ideas with user value
6. Raw-code merge risks and non-goals
7. Minimal implementation slice if approved