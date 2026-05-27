---
description: "Use when editing OpenSpace prompts or host skills that encode planning, search-first decision making, delegation, or verification workflows inspired by external systems such as ECC."
name: "Workflow Surface Reuse"
applyTo: ".github/prompts/*.prompt.md,openspace/host_skills/**"
---
# Workflow Surface Reuse

- Translate external workflow ideas into OpenSpace-native language and tool names. Refer to `execute_task`, `search_skills`, `fix_skill`, `upload_skill`, host skills, prompts, and existing docs instead of harness-specific command names or hook machinery.
- Favor search-first planning. Before introducing a new helper, workflow, or abstraction, check whether the repo, existing host skills, existing prompts, or mounted MCP surfaces already cover the need.
- Keep the core sequence explicit when the workflow is non-trivial: clarify requirements, search existing options, choose adopt or extend or build, implement in bounded slices, then verify.
- Prompts should keep approval gates explicit when they are meant for planning. Host skills should keep delegation bounded and tell the host when to verify results instead of assuming one-shot delegation is always correct.
- Do not import or refer to external harness hooks, installers, marketplace packaging, dashboard code, or full command or agent catalogs unless the user explicitly wants that surrounding system.
- If a workflow recommendation depends on a concrete MCP or external-runtime gap, require evidence from the current repo or a documented external contract before suggesting runtime config changes.
- Prefer linking to existing repo docs rather than embedding long repeated guidance when the documentation already exists nearby.