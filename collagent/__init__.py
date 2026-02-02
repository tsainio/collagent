"""
CollAgent - AI-Powered Research Collaborator Discovery

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

from .base import CollAgentBase
from .core import CollAgentGoogle, HTML_REPORT_TEMPLATE
from .openai_agent import CollAgentOpenAI
from .factory import create_agent
from .config import (
    load_config,
    get_models,
    get_model_by_id,
    get_default_model,
    get_available_models,
    get_provider_config,
)
from .streaming import console, StreamingConsole, search_results, search_results_lock
from .template import WEB_TEMPLATE
from .web import create_web_app, run_web_server, FLASK_AVAILABLE, WEASYPRINT_AVAILABLE
from .cli import main

__version__ = "1.1.0"
__author__ = "Tuomo Sainio"
__license__ = "AGPL-3.0"

__all__ = [
    # Base and agent classes
    "CollAgentBase",
    "CollAgentGoogle",
    "CollAgentOpenAI",
    "create_agent",
    # Configuration
    "load_config",
    "get_models",
    "get_model_by_id",
    "get_default_model",
    "get_available_models",
    "get_provider_config",
    # Streaming
    "StreamingConsole",
    "console",
    # Web
    "create_web_app",
    "run_web_server",
    "main",
    "WEB_TEMPLATE",
    "HTML_REPORT_TEMPLATE",
    "FLASK_AVAILABLE",
    "WEASYPRINT_AVAILABLE",
]
