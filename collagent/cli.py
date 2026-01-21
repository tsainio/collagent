"""
CollAgent - Command Line Interface

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import argparse
import os
import sys
from datetime import datetime

from rich.markdown import Markdown

from .streaming import console
from .core import CollAgentGoogle
from .web import run_web_server


def main():
    parser = argparse.ArgumentParser(
        description="CollAgent - Search for collaborators using Gemini + Google Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Broad search (default when no institution specified)
  %(prog)s --profile "I study machine learning for chemistry"

  # Limit institutions in broad search
  %(prog)s --profile "ML for chemistry" --max-institutions 3

  # Broad search with region filter
  %(prog)s --profile "ML for chemistry" --region "Europe"

  # Single institution search
  %(prog)s --profile "I study machine learning for chemistry" --institution "MIT"
  %(prog)s --profile-file my_research.txt --institution "LUT University"
  %(prog)s --profile "Separation processes" -i "TU Vienna" -o report.md

  # Web interface mode
  %(prog)s --web
  %(prog)s --web --port 8080
        """
    )

    parser.add_argument("--profile", "-p", type=str, help="Your research profile/description")
    parser.add_argument("--profile-file", "-f", type=str, help="File containing your research profile")
    parser.add_argument("--institution", "-i", type=str, help="Target institution to search (single institution mode)")
    parser.add_argument("--focus", type=str, help="Comma-separated focus areas")
    parser.add_argument("--output", "-o", type=str, help="Output file for report (markdown)")
    parser.add_argument("--max-turns", type=int, default=10, help="Max agent turns (default: 10)")
    parser.add_argument("--max-institutions", type=int, default=5,
                       help="Max institutions to search in broad mode (default: 5)")
    parser.add_argument("--region", type=str, help="Region filter for broad search (e.g., 'Europe', 'USA')")
    parser.add_argument("--log", "-l", nargs='?', const='auto', default=None,
                       help="Log file for search process (HTML with colors). Use without value for auto-generated name.")
    parser.add_argument("--top", "-t", type=int, default=5, help="Number of candidates in shortlist (default: 5)")
    parser.add_argument("--model", type=str, default="gemini-3-flash-preview",
                       choices=["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-3-pro-preview"],
                       help="Gemini model (default: gemini-3-flash-preview)")
    parser.add_argument("--web", "-w", action="store_true",
                       help="Start web interface instead of CLI mode")
    parser.add_argument("--port", type=int, default=5000,
                       help="Port for web server (default: 5000)")

    args = parser.parse_args()

    # Web mode - start Flask server
    if args.web:
        run_web_server(port=args.port)
        return

    # CLI mode - require profile
    # Get API key
    api_key = os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        console.print("[red]Error: GOOGLE_API_KEY environment variable not set[/red]")
        console.print("[dim]Get your key at https://aistudio.google.com/apikey[/dim]")
        sys.exit(1)

    # Get profile
    if args.profile_file:
        with open(args.profile_file) as f:
            profile = f.read()
    elif args.profile:
        profile = args.profile
    else:
        console.print("[red]Error: Must provide --profile or --profile-file (or use --web for web mode)[/red]")
        sys.exit(1)

    # Parse focus areas
    focus_areas = [a.strip() for a in args.focus.split(",")] if args.focus else None

    # Create agent and search
    agent = CollAgentGoogle(api_key, model=args.model)

    try:
        if args.institution:
            # Single institution search (existing behavior)
            collaborators = agent.search(
                profile=profile,
                institution=args.institution,
                focus_areas=focus_areas,
                max_turns=args.max_turns
            )
        else:
            # Broad search: discover institutions first (new default)
            collaborators = agent.search_broad(
                profile=profile,
                focus_areas=focus_areas,
                region=args.region,
                max_institutions=args.max_institutions,
                max_turns=args.max_turns
            )

        # Print shortlist table
        agent.print_shortlist(top_n=args.top)

        # Generate report
        report = agent.generate_report(args.output)

        if not args.output:
            console.print("\n")
            console.print(Markdown(report))

    except KeyboardInterrupt:
        console.print("\n[yellow]Search interrupted[/yellow]")
        if agent.collaborators:
            agent.generate_report(args.output or "partial_report.md")

    finally:
        # Save log file if requested
        if args.log:
            if args.log == 'auto':
                log_path = f"collagent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            else:
                log_path = args.log if args.log.endswith('.html') else args.log + '.html'
            console.save_html(log_path, clear=False)
            console.print(f"[green]Log saved to {log_path}[/green]")


if __name__ == "__main__":
    main()
