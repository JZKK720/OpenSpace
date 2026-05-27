---
name: ecc-workflow-curation
description: "Selectively translate useful ECC workflows into OpenSpace host skills, prompts, or instructions instead of copying ECC's full commands, agents, hooks, or runtime surfaces. Use when evaluating ECC commands or skills for reuse inside the Cubecloud OpenSpace fork."
trigger: /ecc-workflow-curation
---

# /ecc-workflow-curation

Turn ECC workflow ideas into the smallest OpenSpace-native surface that preserves user value without importing the whole ECC harness.

## Usage

```text
/ecc-workflow-curation
/ecc-workflow-curation "pick the best ECC workflow ideas for OpenSpace dashboard operators"
/ecc-workflow-curation "translate ECC workflow X into an OpenSpace host skill"
/ecc-workflow-curation "review ECC commands and decide what should be prompt, instruction, host skill, or external runtime"
```

## What This Skill Is For

Use this skill when the user wants reuse, not a repo merge.

Good fits:
- selecting a few ECC workflows that would actually improve OpenSpace
- translating an ECC planning or operator workflow into an OpenSpace host skill
- deciding whether an ECC capability should become a prompt, instruction, host skill, runtime skill, or external runtime integration
- rejecting low-value or high-drift ECC surfaces before they leak into the repo

Not a fit:
- wiring runtime transports or ports without a contract; use [Plan ECC Adapter Contract](../../prompts/ecc-adapter-contract.prompt.md) first
- editing external-agent, standalone-app, dashboard, or Compose surfaces without first classifying the integration boundary; use [Plan ECC Integration](../../prompts/ecc-integration.prompt.md) first
- copying ECC hooks, installers, marketplace assets, or the full commands or agents tree into OpenSpace

## Decision Rules

Map each ECC candidate workflow to exactly one of these destinations:

1. **Host skill** when the workflow should teach an external host agent when and how to call OpenSpace MCP tools.
2. **OpenSpace skill** when the workflow belongs inside OpenSpace's own task execution layer.
3. **Prompt** when the value is a contributor workflow or planning routine rather than a runtime capability.
4. **Instruction** when the rule should always shape edits in a known file slice.
5. **External runtime or deep-link** when the value lives better inside ECC and OpenSpace should only launch or hand work to it.
6. **Reject** when the candidate depends on ECC-specific hooks, harness settings, installer behavior, marketplace packaging, or a large surrounding subsystem.

Choose the smallest destination that preserves the outcome.

## What You Must Do When Invoked

If the user names a specific ECC workflow, review that workflow first.

If the user does not name one, inventory a short list of high-leverage candidates from ECC and classify them before proposing any implementation.

Follow these steps in order:

### Step 1 - Gather the minimum source evidence

Inspect only the ECC sources needed for the requested workflow or shortlist:

- `README.md`
- `AGENTS.md`
- `commands/`
- `skills/`
- `agent.yaml`
- `mcp-configs/`
- any adjacent docs that explain the user-facing outcome

Also inspect the matching OpenSpace destination surfaces:

- [openspace/host_skills/README.md](../../../openspace/host_skills/README.md)
- [openspace/skills/README.md](../../../openspace/skills/README.md)
- [README.md](../../../README.md)
- any existing prompt, instruction, or host-skill files that already cover a nearby workflow

### Step 2 - Extract the user value, not the wrapper

For each candidate, write down:

- the user-facing job to be done
- the minimum inputs it needs
- the output or decision it produces
- whether it depends on ECC-specific hooks, agents, runtime daemons, or marketplace state

Do not copy wording or structure until the value has been separated from the ECC wrapper.

### Step 3 - Classify each candidate

Produce a curation table with these columns:

- candidate
- user value
- target OpenSpace surface
- keep, translate, deep-link, or reject
- rationale

Bias toward rejection when a candidate is mostly harness glue or packaging.

### Step 4 - Translate only if the target is clear

If the user wants implementation and the destination is clear:

- rewrite in OpenSpace terms instead of copying ECC prose
- reference OpenSpace tools, registries, and docs directly
- link to source material instead of embedding large borrowed passages
- keep the translated artifact narrow and testable

If the destination is not clear, stop with the curation table and recommend the next boundary question.

### Step 5 - Validate the destination

Validate based on the target surface:

- customization files: check frontmatter and workspace diagnostics
- host skills or runtime skills: follow the applicable skill-authoring guidance and validate file structure before touching unrelated code
- bridge or runtime surfaces: switch to [Plan ECC Integration](../../prompts/ecc-integration.prompt.md) or [Plan ECC Adapter Contract](../../prompts/ecc-adapter-contract.prompt.md) before implementation

## Output Format

Return these sections in order:

1. Requested or inferred ECC workflow set
2. Curation table
3. Recommended destination per candidate
4. What should not be imported
5. Minimal translation slice if approved