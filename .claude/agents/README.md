# Agents

This directory contains subagent definitions for Claude Code.

## What Are Agents?

Agents are specialized Claude instances invoked via the `Task` tool (or via the `claude` CLI with `--agent`). Each agent has a focused role, a constrained toolset, and a specific behavioral protocol. Using agents prevents context pollution in the main session and enables parallelism.

## Available Agents

| Agent | File | Role | Access |
|-------|------|------|--------|
| `code-reviewer` | `code-reviewer.md` | Review code for correctness, security, and quality | Read-only |
| `debugger` | `debugger.md` | Diagnose and fix bugs systematically | Read + Write |
| `spec-writer` | `spec-writer.md` | Write specs, API docs, ADRs, and READMEs | Read + Write |
| `simplicity-checker` | `simplicity-checker.md` | Detect duplicate logic, reinvented wheels, and over-engineering | Read-only |
| `product-reviewer` | `product-reviewer.md` | Audit UX, workflow fit, naming clarity, and output readability of developer tooling | Read-only |
| `ux-researcher` | `ux-researcher.md` | Map user journeys, assess UI quality, identify missing features, generate new stories — used in planning AND post-implementation phases | Read + Write |
| `pipeline-optimizer` | `pipeline-optimizer.md` | Audit and rewrite Ralph loop, agent, and skill instructions for better outputs | Read + Write |

## How to Use

Claude Code automatically discovers agents in `.claude/agents/`. Reference them in prompts:

```
Use the code-reviewer agent to review my changes before I push.
Use the debugger agent to fix the failing test in auth.test.ts.
Use the spec-writer agent to write an ADR for the caching strategy.
Use the simplicity-checker agent on src/services/payment.ts.
Use the product-reviewer agent on the README and onboarding docs.
Use the ux-researcher agent in planning mode on ralph/prd.json.
Use the ux-researcher agent in post-implementation mode on the user profile feature.
Use the pipeline-optimizer agent — Ralph has been outputting FAILED without clear reasons.
```

## Self-Improving Pipeline

Every agent produces a `FEEDBACK_START...FEEDBACK_END` block at the end of its output. The `pipeline-optimizer` agent consumes these blocks (from logs and session output) to find recurring ambiguities and fix underperforming instructions automatically.

To trigger a pipeline improvement cycle:
```
Use the pipeline-optimizer agent to review recent feedback and improve the pipeline.
```

## Agent Frontmatter Fields

```yaml
---
name: agent-name
description: When Claude should invoke this agent (used for auto-selection)
tools:
  - Read
  - Glob
  - Grep
model: claude-sonnet-4-6          # or claude-opus-4-6 for complex tasks
permissionMode: bypassPermissions  # or default
---
```

## Creating a New Agent

1. Create `<agent-name>.md` in this directory.
2. Add YAML frontmatter with `name`, `description`, `tools`, `model`, `permissionMode`.
3. Write the agent's system prompt below the frontmatter.
4. Be specific about the agent's process, output format, and constraints.
