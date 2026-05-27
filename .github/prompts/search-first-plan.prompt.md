---
description: "Restate requirements, search existing repo patterns, skills, and MCP options before inventing new code, then produce a phased implementation plan with risks, validation, and an approval gate."
name: "Search-First Plan"
argument-hint: "Describe the feature, refactor, integration, or workflow to plan"
agent: agent
tools: [execute, read, search, todo]
---
Use this prompt when the change is large enough that you should search first and plan before editing.

## Default Behavior

- Stay in plan-only mode.
- Restate the request in concrete terms.
- Search the repo for the closest existing patterns before proposing new files, abstractions, or runtime surfaces.
- Check whether the best path is to adopt an existing pattern, extend a nearby surface, or build something new.
- Produce a phased plan and wait for approval before any code changes.

## Required Context

Start with the smallest relevant set of local evidence:

- nearby implementation files
- nearby tests
- relevant prompts or host skills when the request is workflow-oriented
- [README.md](../../README.md), [openspace/skills/README.md](../../openspace/skills/README.md), and [openspace/host_skills/README.md](../../openspace/host_skills/README.md) when the work crosses product or workflow surfaces

If the request involves an integration or a new capability, also check whether an existing MCP surface, external agent, or standalone app already covers part of the need before recommending net-new code.

If the blocking uncertainty is current third-party library, SDK, or API behavior, check a host-side documentation surface such as Context7 after local repo search and before recommending new code, new runtime wiring, or delegation.

If the blocking uncertainty is broader live web evidence rather than library docs, use a host-side web research surface such as Exa in that same post-repo-search slot before recommending new code, new runtime wiring, or delegation.

## Planning Rules

- Capture the best local pattern for naming, error handling, tests, and validation when the repo already provides one.
- If no relevant local pattern exists, say so directly instead of inventing certainty.
- Separate local repo evidence from external documentation or live web evidence. If a recommendation depends on Context7, Exa, or another host-side research surface rather than checked-in code, say so explicitly.
- Keep the choice explicit:
  - **Adopt** when an existing surface already solves the need
  - **Extend** when a nearby surface is the right foundation
  - **Build** when the gap is real and local evidence shows no better reuse path
- Break the work into bounded phases with a validation step for each phase when possible.
- Include risks, dependencies, and open questions.
- End by waiting for user approval.

## Output Format

Return these sections in order:

1. Requirements restatement
2. Existing patterns and reusable surfaces
3. Adopt or extend or build decision
4. Phased implementation plan
5. Validation plan
6. Risks and open questions
7. Approval gate