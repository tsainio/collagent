#!/usr/bin/env python3
"""
CollAgent - Research Collaborator Search Agent

Copyright (C) 2026 Tuomo Sainio

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

---

Vibe coded by Tuomo Sainio, 2026-01-20

Uses Google Gemini with built-in Google Search grounding.
No external search API needed - just your Google API key.

Two-phase approach:
  1. Research phase: Uses Google Search grounding to find researchers
  2. Extraction phase: Uses function calling to structure the results

Requirements:
    pip install google-genai rich python-dotenv

Usage:
    python collagent.py --profile "your research description" --institution "target university"

Environment:
    GOOGLE_API_KEY - Your Gemini API key
"""

from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent
    load_dotenv(script_dir / ".env")
    load_dotenv()
except ImportError:
    pass

from collagent import main

if __name__ == "__main__":
    main()
