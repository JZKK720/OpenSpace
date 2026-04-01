---
description: "Use when writing, editing, or reviewing OpenSpace skills — SKILL.md authoring, frontmatter schema, skill directory layout, safety rules, sidecar files, and skill discovery priority."
applyTo: "openspace/skills/**,openspace/host_skills/**,gdpval_bench/skills/**"
---
# OpenSpace Skill Authoring

## Directory Layout

Each skill is an isolated subdirectory. Only the `SKILL.md` is required; auxiliary files are optional:

```
openspace/skills/
└── my-skill/
    ├── SKILL.md        ← required
    ├── helper.sh       ← optional aux file
    └── data.json       ← optional aux file
```

Loose files at the directory root (e.g. `README.md`) are silently ignored by the scanner.

## SKILL.md Frontmatter

The file **must** start with YAML frontmatter. Both fields are mandatory:

```yaml
---
name: my-skill
description: "Use when <trigger phrase>. Covers <scope>."
---
```

- `name` must match the folder name exactly (case-sensitive).
- `description` is the **primary discovery surface** — include specific trigger keywords agents will match on. Use the "Use when..." pattern.
- Never omit either field; a missing `name` or `description` causes silent load failure.

## Body

The markdown body is the instruction loaded when the skill is selected. Keep it actionable:

- Use numbered steps for multi-stage workflows.
- Prefer concrete examples over prose explanations.
- Reference sibling aux files with a relative path (`./helper.sh`).

## Safety

All skills pass `check_skill_safety` automatically before loading. **Never bypass it.**

Patterns that will be blocked:
- Exfiltrating environment variables or credentials via network calls
- Prompt injection (attempting to override the agent system prompt)
- Shell commands that write outside the workspace or modify system state

If a skill is blocked at startup, a warning is logged — check the runtime log, not the skill file.

## Sidecar `.skill_id` Files

After first discovery, the runtime writes `{name}__imp_{uuid[:8]}` sidecar files alongside `SKILL.md`. These track identity across restarts.

- **Do not commit sidecar files.** They are in `.gitignore`.
- Do not rename a skill folder without also deleting its sidecar; orphaned sidecars cause duplicate-ID warnings.

## Discovery Priority

Skills are resolved in highest-to-lowest order:

1. `OPENSPACE_HOST_SKILL_DIRS` env var (comma-separated paths)
2. `config_grounding.json → skills.skill_dirs`
3. `openspace/skills/` ← this directory (lowest priority)

A skill in a higher-priority source **shadows** one with the same `name` in a lower-priority source. When debugging "wrong skill loaded" issues, check which source wins.

## Registering a New Skill Dir at Runtime

```python
from openspace.skill_engine.registry import register_skill_dir
meta = register_skill_dir("/path/to/skills/my-skill")
# Returns existing SkillMeta if already registered (idempotent)
```

## Cloud Skills

Downloaded cloud skills land in `openspace/skills/` when no other skill directory is configured. Evolved/generated skills are tagged with a hash suffix (`-b8f537`) to avoid name collisions. See `openspace/cloud/` for upload/download CLI.

## References

- Full skill system docs: [openspace/skills/README.md](../../openspace/skills/README.md)
- Host skills (delegate-task, skill-discovery): [openspace/host_skills/](../../openspace/host_skills/)
- Benchmark skill examples: [gdpval_bench/skills/](../../gdpval_bench/skills/)
