<!--
Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
-->

# Using CollAgent from AI Agents

CollAgent's CLI is designed to work as a tool for local AI agents — via MCP servers, function calling, shell tool use, or any framework that can invoke shell commands.

## Quick Example

```bash
python collagent.py \
  -f researcher_profile.txt \
  -o results.md \
  --max-institutions 3 \
  --region "Europe"
```

The agent writes the research profile to a file, runs CollAgent, then reads `results.md` for structured collaborator data.

## Key Behaviors

- **Non-interactive**: All parameters are passed as flags. No interactive prompts or confirmations.
- **Exit codes**: 0 on success, 1 on error (missing API key, unknown model, invalid arguments).
- **Output to file**: Use `-o report.md` to write the markdown report to a predictable path. Without `-o`, the report prints to the console.
- **Profile from file**: Use `-f profile.txt` for research profiles. Better than `-p` for longer text that may have quoting issues in shell arguments.
- **HTML log**: Use `--log search.html` to save the full search process for debugging or review.

## Output Format

The markdown report (`-o`) contains structured sections. In broad mode, collaborators are grouped by institution:

```
# Collaborator Search Report

Generated: 2026-01-15 14:30
Model: ...

## Summary

Found **12** potential collaborators across **3** institutions.

### Institutions Searched
- **MIT** (USA) - Relevance: ★★★★☆

---

## Collaborators by Institution

### MIT (USA)

*4 collaborator(s) found*

#### 1. Researcher Name

**Alignment:** ★★★★☆ (4/5)

| Field | Details |
|-------|---------|
| Position | Associate Professor |
| Email | name@mit.edu |

**Research Focus:** ...
**Why This Match:** ...
**Suggested Collaboration:** ...
**Key Publications:** ...
```

## Recommended Flags for Agent Use

| Flag | Purpose |
|------|---------|
| `-f profile.txt` | Research profile from file (avoids shell quoting issues) |
| `-o results.md` | Write report to file for parsing |
| `--log search.html` | Save full search log for debugging |
| `--max-institutions N` | Control scope (lower = faster, higher = more thorough) |
| `--max-turns N` | Control search depth (default 10, lower for speed) |
| `--region "..."` | Geographic filter |
| `-i "Institution"` | Skip discovery, search one institution directly |
| `--model MODEL` | Choose model (use `--list-models` to enumerate) |

## Docker

For sandboxed execution:

```bash
docker run --rm \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  -v $(pwd)/output:/app/output \
  collagent \
  -f output/profile.txt \
  -o output/results.md \
  --max-institutions 3
```

Mount a volume to share input/output files between the agent and the container.

## Error Handling

CollAgent exits with code 1 and prints errors to the console for:
- Missing or invalid API key
- Unknown model name
- Missing required `--profile` or `--profile-file`

The agent should check the exit code before attempting to read the output file.
