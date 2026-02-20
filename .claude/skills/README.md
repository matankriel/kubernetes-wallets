# Skills

This directory contains skill definitions for Claude Code slash commands.

## What Are Skills?

Skills are slash commands that users can invoke with `/skill-name [args]`. Each skill is a structured prompt that guides Claude through a specific workflow. Unlike agents, skills run in the main session context.

## Available Skills

| Skill | Command | Description |
|-------|---------|-------------|
| `commit` | `/commit` | Lint, test, stage, and commit with conventional commit format |
| `review-pr` | `/review-pr [number]` | Fetch a PR diff via `gh` and review it by category |
| `create-story` | `/create-story [description]` | Append a new story to `ralph/prd.json` |
| `ship` | `/ship` | Full pipeline: lint → test → commit → push → PR |

## Skill Frontmatter Fields

```yaml
---
name: skill-name
description: What this skill does (shown in /help)
argument-hint: "[optional-arg]"        # Shown as hint in UI
allowed-tools:                         # Tools this skill may use
  - Bash
  - Read
  - Edit
context:                               # Files always loaded into context
  - path/to/file.md
---
```

## Creating a New Skill

1. Create a directory `.claude/skills/<skill-name>/`
2. Create `SKILL.md` inside it with YAML frontmatter + the prompt body
3. The skill is immediately available as `/<skill-name>`

## Notes

- Skills run in the main Claude session (they have access to full context)
- For isolated, parallel work — use agents instead
- Keep skill prompts focused on a single workflow
- Use `allowed-tools` to restrict what the skill can do for safety
