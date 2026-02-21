---
name: create-story
description: Interactively create a new story and append it to ralph/prd.json. Prompts for all required fields and shows a preview before writing.
argument-hint: "[brief description]"
allowed-tools:
  - Read
  - Edit
  - Bash
---

# /create-story Skill

You are helping the user create a new story for the Ralph autonomous implementation pipeline. Follow these steps.

## Step 1: Gather Information

If a description was provided as an argument, use it as the starting point. Otherwise, ask for it.

Collect the following fields (use the argument as the description if provided; prompt for the rest):

**Required fields:**
1. **Title** — short, imperative phrase (e.g., "Add rate limiting to API")
2. **Description** — 2-4 sentences explaining what needs to be built
3. **Acceptance Criteria** — 3-5 specific, testable criteria (ask user to provide these)
4. **Priority** — `high` | `medium` | `low`
5. **Type** — `feature` | `bug` | `chore` | `refactor` | `docs`

**Optional fields (offer defaults):**
- **Technical Notes** — implementation hints or constraints (default: empty string)
- **Estimated Complexity** — `XS` | `S` | `M` | `L` | `XL` (default: `M`)
- **Tags** — array of strings (default: `[]`)

## Step 2: Read Current prd.json

Read `ralph/prd.json` to:
1. Determine the next available story ID
2. Confirm the story doesn't duplicate an existing one

The ID format is `STORY-<NNN>` (zero-padded to 3 digits, e.g., `STORY-004`).

## Step 3: Preview

Show the complete story JSON to the user and ask for confirmation:

```
Here's the story I'll add to ralph/prd.json:

{
  "id": "STORY-004",
  "title": "...",
  "status": "pending",
  "priority": "...",
  ...
}

Confirm? (yes/no)
```

## Step 4: Append to prd.json

On confirmation, append the new story to the `stories` array in `ralph/prd.json`.

Use `jq` to safely update the JSON:
```bash
jq '.stories += [<new-story-json>]' ralph/prd.json > ralph/prd.json.tmp && mv ralph/prd.json.tmp ralph/prd.json
```

## Step 5: Confirm

Show the updated story count:
```
Story STORY-004 added. ralph/prd.json now has N stories (M pending).
```

---

## Story Schema Reference

```json
{
  "id": "STORY-XXX",
  "title": "Imperative title",
  "status": "pending",
  "priority": "high|medium|low",
  "type": "feature|bug|chore|refactor|docs",
  "description": "What needs to be built and why.",
  "acceptanceCriteria": [
    "Criterion 1",
    "Criterion 2"
  ],
  "technicalNotes": "Optional implementation hints.",
  "estimatedComplexity": "XS|S|M|L|XL",
  "dependencies": [],
  "tags": []
}
```
