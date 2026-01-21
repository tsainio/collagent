# CollAgent - Research Collaborator Search Agent

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

An AI-powered tool to find potential research collaborators using Google Gemini with built-in Google Search grounding.

## Features

- **Web interface**: Beautiful dark-mode glassmorphism UI with real-time streaming progress
- **Broad search mode** (default): Automatically discovers relevant institutions, then searches each for collaborators
- **Single institution mode**: Target a specific university or research institute
- **Multiple simultaneous searches**: Web interface supports concurrent searches
- **Rich output**: Colored terminal output with shortlist table
- **HTML logs**: Save the complete search process for later review
- **Markdown reports**: Generate detailed reports of potential collaborators

## Requirements

- Python 3.10+
- Google API key with Gemini API access ([Get one here](https://aistudio.google.com/apikey))

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
# Using Docker
docker run --rm -p 5000:5000 -e GOOGLE_API_KEY=your_key collagent --web

# From source
python collagent.py --web
```

Then open http://localhost:5000 in your browser.

### CLI Mode with Docker

```bash
docker run --rm -e GOOGLE_API_KEY=your_key_here collagent \
  -p "machine learning for drug discovery"
```

### CLI Mode from Source

```bash
pip install google-genai rich python-dotenv flask
export GOOGLE_API_KEY="your-gemini-key"

python collagent.py -p "machine learning for drug discovery"
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
# Using the start/stop scripts (recommended)
./start.sh   # Starts on port 5050 by default
./stop.sh    # Stops the container

# Or manually with Docker
docker run --rm -p 5000:5000 -e GOOGLE_API_KEY=your_key collagent --web

# From source
python collagent.py --web --port 5000
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

The easiest way to run the web interface:

```bash
# Start (uses port 5050 by default, reads .env for API key)
./start.sh

# Stop
./stop.sh

# Use custom port
COLLAGENT_PORT=8080 ./start.sh
```

### Docker Web Mode

```bash
# Start web interface
docker run --rm -p 5000:5000 -e GOOGLE_API_KEY=your_key collagent --web

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
| `--port` | Port for web server (default: 5000) |
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
| `--model` | Gemini model (default: gemini-3-flash-preview) * |

## Output

The tool produces:

1. **Terminal output**: Live progress with colored formatting
2. **Shortlist table**: Top candidates displayed as a summary table
3. **Markdown report** (optional): Detailed information grouped by institution
4. **HTML log** (optional): Complete search process with formatting preserved

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  CollAgent                          │
├─────────────────────────────────────────────────────┤
│  Phase 0: Institution Discovery (broad mode)        │
│      └── Finds relevant universities/institutes     │
│                                                     │
│  Phase 1: Research (Google Search grounding)        │
│      └── Searches for researchers at each           │
│          institution                                │
│                                                     │
│  Phase 2: Extraction (Function Calling)             │
│      └── Extracts structured collaborator data      │
│                                                     │
│  Output: Shortlist table + Markdown report          │
└─────────────────────────────────────────────────────┘
```

## Model Options

```bash
--model gemini-3-flash-preview  # Default, fast
--model gemini-2.5-flash        # Alternative
--model gemini-3-pro-preview    # Higher quality, slower
```

## Limitations

- May not find researchers without strong web presence
- Rate limits apply to API calls
- Best for exploratory searches, not exhaustive surveys

## License

Copyright (C) 2026 Tuomo Sainio

This program is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
See [LICENSE](LICENSE) for details.
