# CollAgent - Research Collaborator Search Agent

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

An AI-powered tool to find potential research collaborators using Google Gemini, OpenAI GPT, or local models (Ollama, vLLM, LM Studio). Supports web search via built-in provider tools (Google, OpenAI) or external APIs (Brave, Tavily).

## Features

- **Broad search mode** (default): Discovers relevant institutions automatically, then searches each for collaborators
- **Single institution mode**: Target a specific university or research institute
- **Flexible model routing**: Use different providers for search and processing — e.g. Brave for web search, Gemini for processing
- **External search tools**: Use Tavily or Brave Search as alternatives to built-in provider search
- **Local model support**: Any OpenAI-compatible API (Ollama, vLLM, LM Studio) works out of the box
- **Web and CLI interfaces**: Real-time streaming progress, concurrent searches, downloadable reports (HTML, Markdown, PDF)

## Requirements

- Python 3.10+
- At least one of:
  - Google API key for Gemini models ([Get one here](https://aistudio.google.com/apikey))
  - OpenAI API key for GPT models ([Get one here](https://platform.openai.com/api-keys))
  - A local OpenAI-compatible model (Ollama, vLLM, LM Studio) — no cloud API key needed
- For web search with local models, an external search tool API key:
  - Tavily API key ([tavily.com](https://tavily.com))
  - Brave Search API key ([brave.com/search/api](https://brave.com/search/api/))

## Quick Start

### Web Interface (Recommended)

```bash
# Local Python
./start-without-docker.sh          # Press Ctrl+C to stop

# Docker
./start-docker.sh                  # Runs in background
./stop-docker.sh                   # Stop container
```

Then open http://localhost:5050 in your browser.

Both scripts use port 5050 by default and read API keys from `.env`:

```bash
GOOGLE_API_KEY=your-google-key
OPENAI_API_KEY=your-openai-key
BRAVE_SEARCH_API_KEY=your-brave-key    # optional
TAVILY_API_KEY=your-tavily-key          # optional
```

```bash
# Use custom port
COLLAGENT_PORT=8080 ./start-docker.sh
```

### CLI

```bash
pip install -r requirements.txt

export GOOGLE_API_KEY="your-gemini-key"

# Broad search — discovers institutions, then searches each
python collagent.py -p "ML for chemical engineering"

# Limit to European institutions
python collagent.py -p "ML for chemical engineering" \
  --max-institutions 3 --region "Europe"

# Target a specific institution
python collagent.py -p "machine learning applications in chemical engineering" \
  -i "TU Vienna"

# With output files
python collagent.py -p "generative AI for process design" \
  -o report.md --log search_log

# From a profile file (see example_profile.txt)
python collagent.py -f example_profile.txt --max-institutions 5
```

**Windows users:** Use `requirements-windows.txt` instead (excludes WeasyPrint/PDF export).

### Docker CLI

```bash
docker run --rm -e GOOGLE_API_KEY=your_key collagent \
  -p "machine learning for drug discovery"

docker run --rm -e GOOGLE_API_KEY=your_key collagent \
  -p "quantum computing" -i "MIT" --region "Europe"
```

For using CollAgent as a tool from AI agents, see [docs/agent-usage.md](docs/agent-usage.md).

## Model Configuration

List available models and search tools:
```bash
python collagent.py --list-models
```

### Local / OpenAI-Compatible Models

Any model served via an OpenAI-compatible API (Ollama, vLLM, LM Studio, llama.cpp server) can be used. Add it to `collagent/models.yaml`:

```yaml
models:
  # Search + processing model (pair with Brave/Tavily for web search)
  - id: qwen3:14b
    display_name: "Qwen3 14B (Ollama)"
    provider: openai_compatible
    base_url: "http://localhost:11434/v1"

  # Extraction-only model (appears only in Processing Model dropdown)
  - id: llama3.3
    display_name: "Llama 3.3 70B (Ollama)"
    provider: openai_compatible
    base_url: "http://localhost:11434/v1"
    processing_only: true
```

When running in Docker, use `http://host.docker.internal:11434/v1` instead of `localhost` to reach Ollama on the host machine.

Pre-configured models appear as regular options in the web UI dropdowns. The web UI also has a "Custom (local model)..." option for ad-hoc use without editing config files.

## Search Tools and Processing Models

By default, a single AI model handles both web search and data extraction. You can also mix providers — e.g. Brave Search for web queries, a local Ollama model for extraction, or any combination. See [docs/architecture.md](docs/architecture.md) for details, pipeline diagram, and CLI examples.

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

## License

Copyright (C) 2026 Tuomo Sainio

This program is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
See [LICENSE](LICENSE) for details.
