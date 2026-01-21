"""
CollAgent - AI-Powered Research Collaborator Discovery

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

from .core import CollAgentGoogle, HTML_REPORT_TEMPLATE
from .streaming import console, StreamingConsole, search_results, search_results_lock
from .template import WEB_TEMPLATE
from .web import create_web_app, run_web_server, FLASK_AVAILABLE, WEASYPRINT_AVAILABLE
from .cli import main

__version__ = "1.0.0"
__author__ = "Tuomo Sainio"
__license__ = "AGPL-3.0"

__all__ = [
    "CollAgentGoogle",
    "StreamingConsole",
    "console",
    "create_web_app",
    "run_web_server",
    "main",
    "WEB_TEMPLATE",
    "HTML_REPORT_TEMPLATE",
    "FLASK_AVAILABLE",
    "WEASYPRINT_AVAILABLE",
]
