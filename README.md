# CollAgent - Research Collaborator Search Agent

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

An AI-powered tool to find potential research collaborators using Google Gemini or OpenAI GPT models with web search capabilities.

## Features

- **Web interface**: Beautiful dark-mode glassmorphism UI with real-time streaming progress
- **Broad search mode** (default): Automatically discovers relevant institutions, then searches each for collaborators
- **Single institution mode**: Target a specific university or research institute
- **Multiple simultaneous searches**: Web interface supports concurrent searches
- **Rich output**: Colored terminal output with shortlist table
- **HTML logs**: Save the complete search process for later review
- **Markdown reports**: Generate detailed reports of potential collaborators
- **Flexible model routing**: Use different models for search and extraction (e.g. Google for search, local Ollama for extraction)
- **External search tools**: Use Tavily or Brave Search instead of the built-in provider search

## Requirements

- Python 3.10+
- At least one AI model API key:
  - Google API key for Gemini models ([Get one here](https://aistudio.google.com/apikey))
  - OpenAI API key for GPT models ([Get one here](https://platform.openai.com/api-keys))
- Optionally, an external search tool API key:
  - Tavily API key ([tavily.com](https://tavily.com))
  - Brave Search API key ([brave.com/search/api](https://brave.com/search/api/))

## Installation

```bash
pip install -r requirements.txt
```

**Windows users:** Use `requirements-windows.txt` instead. This excludes WeasyPrint, which requires GTK3 and other system libraries that are difficult to install on Windows. PDF export will be unavailable, but all other features work normally.

```bash
pip install -r requirements-windows.txt
```

## Quick Start

### Web Interface (Recommended)

The easiest way to use CollAgent is through its web interface:

```bash
# Local Python (recommended for development)
./start-without-docker.sh

# Using Docker
./start-docker.sh
```

Then open http://localhost:5050 in your browser. Press Ctrl+C to stop (local) or run `./stop-docker.sh` (Docker).

### CLI Mode from Source

```bash
pip install -r requirements.txt

# Set at least one API key
export GOOGLE_API_KEY="your-gemini-key"
# and/or
export OPENAI_API_KEY="your-openai-key"

python collagent.py -p "machine learning for drug discovery"

# Use a specific model
python collagent.py -p "machine learning" --model gpt-5.2
```

### CLI Mode with Docker

```bash
docker run --rm -e GOOGLE_API_KEY=your_key_here collagent \
  -p "machine learning for drug discovery"
```

## Usage

### Broad Search (default)

When no institution is specified, CollAgent discovers relevant institutions first, then searches each:

```bash
# Discovers top institutions and searches each
python collagent.py -p "ML for chemical engineering"

# Limit to 3 institutions, European region
python collagent.py -p "ML for chemical engineering" \
  --max-institutions 3 \
  --region "Europe"
```

### Single Institution Search

```bash
python collagent.py \
  -p "machine learning applications in chemical engineering" \
  -i "TU Vienna"
```

### With Output Files

```bash
python collagent.py \
  -p "generative AI for process design" \
  -o report.md \
  --log search_log
```

### Using a Profile File

See `example_profile.txt` for a detailed example, or create your own:

```bash
# Use the included example
python collagent.py -f example_profile.txt --max-institutions 5

# Or create your own profile file
python collagent.py -f my_profile.txt --max-institutions 5
```

## Web Interface

The web interface provides a beautiful dark-mode glassmorphism UI with real-time streaming output:

```bash
# Local Python (runs in foreground, Ctrl+C to stop)
./start-without-docker.sh

# Docker (runs in background)
./start-docker.sh
./stop-docker.sh

# Or manually
python collagent.py --web --port 5050
```

### Features

- **Real-time streaming**: Watch the search progress as it happens
- **Multiple concurrent searches**: Each search runs in its own session
- **Full parameter control**: All CLI options available in the web UI
  - Focus areas for targeted searches
  - Max search turns (depth of search)
  - Top candidates to highlight
  - Region and institution filters
  - Model selection
- **Smart results display**:
  - Top N candidates highlighted with badges
  - Remaining candidates in collapsible "Other Candidates" section
- **Download results**: Get HTML or PDF reports
- **Responsive design**: Works on desktop and mobile

### Start/Stop Scripts

**Local Python** (runs in foreground):
```bash
./start-without-docker.sh          # Press Ctrl+C to stop
```

**Docker** (runs in background):
```bash
./start-docker.sh         # Starts container, auto-builds image if needed
./stop-docker.sh          # Stops container
```

Both scripts use port 5050 by default and read API keys from `.env`.

```bash
# Use custom port
COLLAGENT_PORT=8080 ./start-without-docker.sh
COLLAGENT_PORT=8080 ./start-docker.sh
```

### Manual Docker

```bash
# Start web interface
docker run --rm -p 5050:5050 -e GOOGLE_API_KEY=your_key collagent --web --port 5050

# Custom port
docker run --rm -p 8080:8080 -e GOOGLE_API_KEY=your_key collagent --web --port 8080
```

## Docker CLI Usage

```bash
# Basic broad search
docker run --rm -e GOOGLE_API_KEY=your_key collagent \
  -p "machine learning for drug discovery"

# Single institution
docker run --rm -e GOOGLE_API_KEY=your_key collagent \
  -p "quantum computing" -i "MIT"

# With output files (mount a volume)
docker run --rm -e GOOGLE_API_KEY=your_key \
  -v $(pwd)/output:/app/output \
  collagent \
  -p "sustainable chemistry" \
  -o output/report.md \
  --log output/search_log

# European institutions only
docker run --rm -e GOOGLE_API_KEY=your_key collagent \
  -p "protein engineering" \
  --region "Europe" \
  --max-institutions 3
```

## Command-line Options

All options marked with * are also available in the web interface.

| Option | Description |
|--------|-------------|
| `-w, --web` | Start web interface instead of CLI mode |
| `--port` | Port for web server (default: 5050) |
| `-p, --profile` | Your research profile/description (required for CLI) * |
| `-f, --profile-file` | File containing your research profile * |
| `-i, --institution` | Target institution (enables single institution mode) * |
| `--focus` | Comma-separated focus areas * |
| `-o, --output` | Output file for markdown report |
| `-l, --log` | HTML log file (use without value for auto-generated name) |
| `-t, --top` | Number of top candidates to highlight (default: 5) * |
| `--max-institutions` | Max institutions in broad search (default: 5) * |
| `--region` | Region filter for broad search (e.g., "Europe", "USA") * |
| `--max-turns` | Search depth - total budget across phases (default: 10) * |
| `--model` | AI model to use (default: gemini-3-flash-preview) * |
| `--list-models` | Show all available models and search tools |
| `--search-tool` | External search tool: `tavily` or `brave` |
| `--search-tool-api-key` | API key for the external search tool |
| `--processing-model` | Separate model for data extraction (default: same as main model) |
| `--processing-base-url` | Base URL for processing model API (e.g., `http://localhost:11434/v1`) |
| `--processing-api-key` | API key for processing model |

## Model Options

List available models and search tools:
```bash
python collagent.py --list-models
```

### Google Gemini Models
```bash
--model gemini-3-flash-preview  # Default, fast
--model gemini-3-pro-preview    # Higher quality, slower
```

### OpenAI GPT Models
```bash
--model gpt-5.2                 # GPT-5.2 Thinking
--model gpt-5.2-chat-latest     # GPT-5.2 Instant (Fast)
--model gpt-5.2-pro             # GPT-5.2 Pro (Highest Quality)
```

### Local / OpenAI-Compatible Models

Any model served via an OpenAI-compatible API (Ollama, vLLM, LM Studio, llama.cpp server) can be used for extraction. Add it to `collagent/models.yaml`:

```yaml
models:
  - id: llama3.3
    display_name: "Llama 3.3 70B (Ollama)"
    provider: openai_compatible
    base_url: "http://localhost:11434/v1"
    processing_only: true   # won't appear as a search model
```

Only models with configured API keys (or a `base_url` for local models) will be available.

## Separating Search and Extraction

CollAgent supports using different models for the two phases of a search:

- **Search phase**: drives web queries, synthesizes research text (needs internet access or an external search tool)
- **Extraction phase**: reads the research text and outputs structured data (no internet needed)

This is useful when you want a fast/cheap cloud model for search but a local model for extraction, or vice versa.

### External Search Tools

Instead of using the built-in provider search (Google grounding / OpenAI web search), you can plug in Tavily or Brave:

```bash
# Set API key via environment (recommended)
export TAVILY_API_KEY="tvly-..."
export BRAVE_SEARCH_API_KEY="BSA..."

# Use Tavily for search with any model
python collagent.py -p "ML researcher" -m gpt-5.2 --search-tool tavily

# Pass API key directly
python collagent.py -p "ML researcher" --search-tool brave \
  --search-tool-api-key "BSA..."
```

### Processing Model Override

Use a different model for the extraction phase:

```bash
# Google search + local Llama for extraction
python collagent.py -p "ML researcher" -m gemini-3-flash-preview \
  --processing-model llama3.3 \
  --processing-base-url http://localhost:11434/v1

# OpenAI search + different Google model for extraction
python collagent.py -p "ML researcher" -m gpt-5.2 \
  --processing-model gemini-3-pro-preview

# Fully local: Tavily for search + local model for everything
python collagent.py -p "ML researcher" \
  --processing-base-url http://localhost:11434/v1 \
  --processing-model llama3.3 \
  --search-tool tavily
```

## Architecture

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

The search and processing models can be independently configured. Search requires internet access (or a search tool API key); extraction only needs text in, structured data out.

## Output

The tool produces:

1. **Terminal output**: Live progress with colored formatting
2. **Shortlist table**: Top candidates displayed as a summary table
3. **Markdown report** (optional): Detailed information grouped by institution
4. **HTML log** (optional): Complete search process with formatting preserved

## Limitations

- May not find researchers without strong web presence
- Rate limits apply to API calls
- Best for exploratory searches, not exhaustive surveys

## License

Copyright (C) 2026 Tuomo Sainio

This program is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
See [LICENSE](LICENSE) for details.
