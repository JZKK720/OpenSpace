---
description: "Inventory ECC's concrete HTTP, MCP, and UI surfaces and produce a proposed OpenSpace adapter contract before runtime integration work begins."
name: "Plan ECC Adapter Contract"
argument-hint: "Describe the target flow, e.g. 'design the ECC handoff and status contract for OpenSpace dashboard integration'"
agent: agent
tools: [execute, read, search, todo]
---
Use the **ECC Integration** agent (@ecc-integration) when the next step is to move from high-level brainstorming into a concrete bridge contract.

## Default Behavior

- Stay in plan-only mode.
- Inventory OpenSpace's available integration contracts first.
- Inventory ECC's concrete public endpoints, transports, and UI surfaces second.
- Produce a proposed adapter contract for the smallest viable OpenSpace integration boundary.
- Do not edit code, config, Compose, or docs until the contract is accepted.

## Required Context

For OpenSpace, start with:

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

For ECC, inspect whichever of these surfaces exist and are relevant:

- `README.md`
- `AGENTS.md`
- `package.json`
- `pyproject.toml`
- `agent.yaml`
- `ecc_dashboard.py`
- `mcp-configs/`
- `commands/`
- `skills/`
- `ecc2/`
- any public API docs, Dockerfiles, or launch scripts that reveal ports, transports, auth, or UI routes

## Contract Checklist

For each plausible integration shape, explicitly inventory:

- transport and protocol
- base URL and port
- health URL and status semantics
- action, handoff, or tool endpoint
- auth requirements and env names
- request schema
- response schema
- streaming vs request-response behavior
- session, history, or thread model
- timeout, retry, and failure envelope
- UI URL or dashboard surface, if any
- Compose or container assumptions

If any item cannot be verified from source evidence, mark it as unknown and stop short of implementation advice that depends on it.

## Planning Rules

- Prefer the smallest viable contract. If ECC already matches an OpenSpace-supported protocol, recommend config-driven registration before new adapter code.
- Separate browse, handoff, and tool surfaces. A standalone app card, an external-agent handoff, and an MCP server are different contracts even if ECC exposes all three.
- Use OpenHuman only as a reference for deeper protocol adaptation, not as the default template.
- If the real gap is missing ECC documentation rather than missing OpenSpace capability, say so directly and describe the minimum additional evidence needed.
- Recommend env names, ids, and URLs that fit OpenSpace conventions, but do not invent endpoint paths for ECC.

## Output Format

Return these sections in order:

1. Target user-facing flow
2. OpenSpace contract options
3. Verified ECC endpoint inventory
4. Proposed adapter contract
5. Required env vars and config fields
6. Unknowns or blockers
7. Minimal implementation slice after approval