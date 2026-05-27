---
name: phased-delegation
description: Use when a task is multi-step, risky, or unclear enough that you should search for existing skills first, delegate work in bounded phases, and verify results before reporting completion.
---

# Phased Delegation

OpenSpace is connected as an MCP server. Whether the host uses `stdio`, `sse`, or `streamable-http`, you have the same 4 tools available: `execute_task`, `search_skills`, `fix_skill`, `upload_skill`.

## When to use

- **The task is non-trivial** — it spans discovery, implementation, validation, or multiple systems
- **Risk is meaningful** — wrong output would waste time or cause regressions
- **You suspect reuse exists** — there may already be a local or cloud skill worth following
- **One-shot delegation feels too vague** — the task needs phases, not a single umbrella prompt

## Workflow

### 1. Frame the task before delegating

Write down:

- the concrete goal
- important constraints
- what would count as success
- what needs validation before you call it done

If the request is still ambiguous, clarify it first instead of passing that ambiguity downstream.

### 2. Search first

Use `search_skills` before reaching for `execute_task`.

```
search_skills(query="docker health checks with restart policy", source="all")
```

If the missing piece is current third-party library, SDK, or API behavior rather than workflow reuse, pause before `execute_task` and check a host-side documentation surface such as Context7. If the missing piece is broader live web evidence, recent announcements, or page content, pause and use a host-side web research surface such as Exa. Bring the confirmed details back into the next phase instead of delegating documentation ambiguity.

Check whether the result suggests:

- **Follow it yourself** — the skill is clear and you already have the needed capability
- **Delegate a bounded phase** — OpenSpace should perform one concrete slice
- **Delegate the whole task** — only when the task is already well-scoped and success criteria are clear

Do not skip this step just because delegation is available.

### 3. Delegate in bounded phases when the task is risky

For large or uncertain tasks, prefer separate calls such as:

- discovery or planning
- implementation
- verification

Example:

```
execute_task(
  task="Inspect the repo's existing Docker health-check patterns and propose the smallest change set to add health checks for service X. Do not edit files.",
  search_scope="all",
  max_iterations=12
)
```

Then follow with a narrower execution call only after you understand the result.

Use a single end-to-end `execute_task` only when the task is already well bounded.

### 4. Verify before you report success

After every `execute_task` result, check whether OpenSpace returned concrete proof:

- changed files or artifacts
- commands run
- validations performed
- unresolved risks or failures

If the result is missing proof, do one of these before reporting completion:

- ask OpenSpace for a focused verification pass
- run your own validation with the host's tools
- tell the user the work is incomplete

Do not translate "task completed" into "done" unless validation exists.

### 5. Repair or upload deliberately

Use `fix_skill` when a specific skill is broken and the failure is local enough to describe precisely.

```
fix_skill(
  skill_dir="/path/to/skills/example-skill",
  direction="The endpoint now requires bearer auth and returns a different status field. Update the skill instructions and examples."
)
```

If OpenSpace evolves or fixes a skill, decide whether to upload it only after checking whether the improvement is reusable or project-specific.

## Decision Guide

```
Need help from OpenSpace?
├── Existing skill is clear and I can follow it myself
│   → Follow the skill directly
├── Task is large or risky
│   → Search first, then delegate in phases
├── Task is well-scoped and success criteria are clear
│   → Delegate with one execute_task call
└── Skill or workflow is broken
    → Use fix_skill with a precise direction
```

## Notes

- `search_skills` is the default first step for complex work.
- Recommended order for external-library or live-web work: local repo evidence, `search_skills`, Context7 if current library or API docs are missing, Exa if broader live web evidence is missing, then `execute_task`.
- `execute_task` is strongest when you pass a bounded objective with clear validation expectations.
- Tell the user what OpenSpace actually did, what it proved, and what still needs attention.