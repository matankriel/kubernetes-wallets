# Commands (Legacy)

This directory contains legacy slash-command definitions (Markdown files read directly as prompts).

## Note on Commands vs Skills

The modern approach is to use **Skills** (`.claude/skills/<name>/SKILL.md`) which support YAML frontmatter for metadata, tool restrictions, and context loading.

Commands in this directory are the older format — a bare Markdown file whose content is injected as the prompt when the user types `/<filename>`. They still work but offer less control.

**Prefer creating new automations as Skills.**

## Available Commands

| Command | File | Description |
|---------|------|-------------|
| `/standup` | `standup.md` | Generate a standup update from recent git activity |

## Creating a Legacy Command

1. Create `<command-name>.md` in this directory.
2. Write the prompt that Claude should follow.
3. The command is available as `/<command-name>`.

No frontmatter is required (or supported) — the entire file content is the prompt.
