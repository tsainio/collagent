<!--
Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
-->

# Architecture: Search Tools and Processing Models

CollAgent's search has two core phases, plus an institution discovery step in broad mode:

- **Discovery phase** (broad mode only): identifies relevant institutions to search
- **Research phase**: drives web queries, synthesizes research text
- **Extraction phase**: reads the research text and outputs structured data

By default, a single AI model (e.g. Gemini, GPT) handles both phases using its built-in web search. For more flexibility, you can use an external search tool and/or a separate processing model.

## Search Tool Options

| Tool | Type | Description |
|------|------|-------------|
| Gemini models | AI model with built-in search | Handles both search and processing |
| GPT models | AI model with built-in search | Handles both search and processing |
| Local model + Brave/Tavily | AI model + external search | Local model processes; external tool searches |
| Brave Search | Search-only API | Requires a separate AI model for processing |
| Tavily | Search-only API | Requires a separate AI model for processing |

In the web UI, the **Search Tool** dropdown lists all options. When you select a search-only tool (Brave/Tavily), a **Processing Model** dropdown appears.

## Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                        CollAgent                            │
├─────────────────────────────────────────────────────────────┤
│  Phase 0: Institution Discovery (broad mode)                │
│      └── Search LLM + search tool finds institutions        │
│                                                             │
│  Phase 1: Research                                          │
│      └── Search LLM + search tool gathers researcher info   │
│          • Built-in: Google grounding / OpenAI web search   │
│          • External: Tavily, Brave (via --search-tool)      │
│                                                             │
│  Phase 2: Extraction                                        │
│      └── Processing LLM extracts structured data           │
│          • Default: same model as search                    │
│          • Override: --processing-model (any provider)      │
│                                                             │
│  Output: Shortlist table + Markdown report                  │
└─────────────────────────────────────────────────────────────┘
```

Search requires internet access (via built-in search or an external search tool API key); extraction only needs text in, structured data out.

## CLI Examples

```bash
# Brave for search, Gemini for processing
python collagent.py -p "ML researcher" -m gemini-3-flash-preview --search-tool brave

# Google search + local Ollama for extraction
python collagent.py -p "ML researcher" -m gemini-3-flash-preview \
  --processing-model llama3.3 \
  --processing-base-url http://localhost:11434/v1

# Brave for search + local model for extraction
python collagent.py -p "ML researcher" \
  --search-tool brave \
  --processing-model llama3.3 \
  --processing-base-url http://localhost:11434/v1
```
