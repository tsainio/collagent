"""
CollAgent - Flask Web Application

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import json
import os
import sys
import threading
import uuid
from datetime import datetime
from queue import Queue

from google.genai import types

from rich.panel import Panel

from .template import WEB_TEMPLATE
from .streaming import console, search_results, search_results_lock, StreamingConsole
from .core import CollAgentGoogle, HTML_REPORT_TEMPLATE

# Flask imports (optional for web mode)
try:
    from flask import Flask, Response, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# PDF generation (optional)
try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


def create_web_app():
    """Create and configure the Flask web application."""
    if not FLASK_AVAILABLE:
        raise ImportError("Flask is not installed. Install with: pip install flask")

    app = Flask(__name__)

    @app.route('/')
    def index():
        """Serve the main web interface."""
        pdf_style = "" if WEASYPRINT_AVAILABLE else "display: none;"
        return WEB_TEMPLATE.replace("{{PDF_BUTTON_STYLE}}", pdf_style)

    @app.route('/search')
    def search():
        """Handle search requests with SSE streaming."""
        profile = request.args.get('profile', '').strip()
        institution = request.args.get('institution', '').strip() or None
        region = request.args.get('region', '').strip() or None
        focus = request.args.get('focus', '').strip() or None
        max_institutions = int(request.args.get('max_institutions', 5))
        max_turns = int(request.args.get('max_turns', 10))
        top_candidates = int(request.args.get('top_candidates', 5))
        model = request.args.get('model', 'gemini-3-flash-preview')

        # Parse focus areas
        focus_areas = [a.strip() for a in focus.split(",") if a.strip()] if focus else None

        if not profile:
            def error_gen():
                yield f"data: {json.dumps({'type': 'error', 'text': 'Profile is required'})}\n\n"
            return Response(error_gen(), mimetype='text/event-stream')

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            def error_gen():
                yield f"data: {json.dumps({'type': 'error', 'text': 'GOOGLE_API_KEY not configured on server'})}\n\n"
            return Response(error_gen(), mimetype='text/event-stream')

        def generate():
            search_id = str(uuid.uuid4())
            output_queue = Queue()
            streaming_console = StreamingConsole(output_queue)

            # Create agent with streaming console
            agent = CollAgentGoogle(api_key, model=model, output_console=streaming_console)

            # Run search in background thread
            def run_search():
                try:
                    if institution:
                        agent.search(
                            profile=profile,
                            institution=institution,
                            focus_areas=focus_areas,
                            max_turns=max_turns
                        )
                    else:
                        agent.search_broad(
                            profile=profile,
                            focus_areas=focus_areas,
                            region=region,
                            max_institutions=max_institutions,
                            max_turns=max_turns
                        )

                    # Generate HTML report
                    report_md = agent.generate_report()

                    # Helper function to format email as clickable link
                    def format_email(email):
                        if not email or email == "N/A":
                            return "N/A"
                        return f'<a href="mailto:{email}">{email}</a>'

                    # Helper function to generate collaborator card HTML
                    def collaborator_card(i, c, is_top=False, search_id=None):
                        from urllib.parse import quote
                        score = c.get("alignment_score", 0)
                        stars = "★" * score + "☆" * (5 - score)
                        top_class = " top-candidate" if is_top else ""
                        badge = '<span class="top-badge">TOP</span>' if is_top else ""
                        name = c.get("name", "Unknown")
                        institution = c.get("institution", "N/A")
                        email = c.get("email", "")
                        collab_id = f"collab-{i}"

                        # Build Google Search URL
                        query_parts = [name]
                        if institution and institution != 'N/A':
                            query_parts.append(institution)
                        if email and email != 'N/A':
                            query_parts.append(email)
                        search_url = f"https://www.google.com/search?q={quote(' '.join(query_parts))}"

                        return f'''
                        <div class="collaborator{top_class}" id="{collab_id}">
                            <h3>{i}. {name}{badge}</h3>
                            <p class="score">{stars} ({score}/5)</p>
                            <table>
                                <tr><th>Position</th><td>{c.get("position", "N/A")}</td></tr>
                                <tr><th>Institution</th><td>{institution}</td></tr>
                                <tr><th>Email</th><td>{format_email(c.get("email"))}</td></tr>
                                <tr>
                                    <th>Website</th>
                                    <td class="website-cell" id="website-{collab_id}">
                                        <a href="{search_url}" target="_blank" class="btn-find-page">🔍 Google Search</a>
                                    </td>
                                </tr>
                            </table>
                            <div class="field">
                                <p class="field-label">Research Focus</p>
                                <p class="field-value">{c.get("research_focus", "N/A")}</p>
                            </div>
                            <div class="field">
                                <p class="field-label">Why This Match</p>
                                <p class="field-value">{c.get("alignment_reasons", "N/A")}</p>
                            </div>
                            <div class="field">
                                <p class="field-label">Collaboration Angle</p>
                                <p class="field-value">{c.get("collaboration_angle", "N/A")}</p>
                            </div>
                        </div>
                        '''

                    # Build HTML content from collaborators
                    content_html = f"<div class='summary'><p>Found <strong>{len(agent.collaborators)}</strong> potential collaborators"
                    if agent.searched_institutions:
                        content_html += f" across <strong>{len(agent.searched_institutions)}</strong> institutions"
                    content_html += f". Showing top <strong>{min(top_candidates, len(agent.collaborators))}</strong> highlighted below.</p></div>"

                    # Sort by alignment score
                    sorted_collabs = sorted(
                        agent.collaborators,
                        key=lambda x: x.get("alignment_score", 0),
                        reverse=True
                    )

                    # Split into top candidates and others
                    top_collabs = sorted_collabs[:top_candidates]
                    other_collabs = sorted_collabs[top_candidates:]

                    # Add top candidates section
                    if top_collabs:
                        content_html += f'<h2 class="section-header">Top {len(top_collabs)} Candidates</h2>'
                        for i, c in enumerate(top_collabs, 1):
                            content_html += collaborator_card(i, c, is_top=True)

                    # Add other candidates in collapsible section
                    if other_collabs:
                        content_html += f'''
                        <div class="collapsible-header">
                            <h3>Other Candidates ({len(other_collabs)} more)</h3>
                            <span class="collapsible-icon">▼</span>
                        </div>
                        <div class="collapsible-content">
                        '''
                        for i, c in enumerate(other_collabs, len(top_collabs) + 1):
                            content_html += collaborator_card(i, c, is_top=False)
                        content_html += '</div>'

                    html_report = HTML_REPORT_TEMPLATE.format(
                        content=content_html,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )

                    # Store results
                    with search_results_lock:
                        search_results[search_id] = {
                            'html': html_report,
                            'markdown': report_md,
                            'collaborators': agent.collaborators,
                            'timestamp': datetime.now()
                        }

                    output_queue.put({
                        'type': 'complete',
                        'search_id': search_id,
                        'count': len(agent.collaborators)
                    })

                except Exception as e:
                    output_queue.put({'type': 'error', 'text': str(e)})

            # Start search thread
            search_thread = threading.Thread(target=run_search, daemon=True)
            search_thread.start()

            # Yield status update
            yield f"data: {json.dumps({'type': 'status', 'text': 'Search in progress...'})}\n\n"

            # Stream output from queue
            while True:
                try:
                    msg = output_queue.get(timeout=60)
                    yield f"data: {json.dumps(msg)}\n\n"

                    if msg.get('type') in ('complete', 'error'):
                        break
                except Exception:
                    yield f"data: {json.dumps({'type': 'error', 'text': 'Search timeout'})}\n\n"
                    break

        return Response(generate(), mimetype='text/event-stream',
                       headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.route('/results/<search_id>')
    def results(search_id):
        """Serve search results as HTML or PDF."""
        with search_results_lock:
            result = search_results.get(search_id)

        if not result:
            return "Results not found or expired", 404

        download = request.args.get('download', '')

        if download == 'html':
            return Response(
                result['html'],
                mimetype='text/html',
                headers={'Content-Disposition': f'attachment; filename=collagent_report_{search_id[:8]}.html'}
            )
        elif download == 'md':
            return Response(
                result['markdown'],
                mimetype='text/markdown',
                headers={'Content-Disposition': f'attachment; filename=collagent_report_{search_id[:8]}.md'}
            )
        elif download == 'pdf':
            if not WEASYPRINT_AVAILABLE:
                return "PDF generation not available", 500
            try:
                pdf_bytes = WeasyHTML(string=result['html']).write_pdf()
                return Response(
                    pdf_bytes,
                    mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename=collagent_report_{search_id[:8]}.pdf'}
                )
            except Exception as e:
                return f"PDF generation failed: {e}", 500

        return result['html']

    return app


def run_web_server(port: int = 5000):
    """Run the Flask web server."""
    if not FLASK_AVAILABLE:
        console.print("[red]Error: Flask is not installed[/red]")
        console.print("[dim]Install with: pip install flask[/dim]")
        sys.exit(1)

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Error: GOOGLE_API_KEY environment variable not set[/red]")
        console.print("[dim]Get your key at https://aistudio.google.com/apikey[/dim]")
        sys.exit(1)

    app = create_web_app()

    console.print(Panel(
        f"[bold]CollAgent Web Interface[/bold]\n\n"
        f"URL: http://0.0.0.0:{port}\n"
        f"API Key: {'*' * 8}...{api_key[-4:]}\n\n"
        f"Press Ctrl+C to stop",
        title="Web Server",
        border_style="green"
    ))

    # Run Flask (use threaded=True for concurrent requests)
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)

