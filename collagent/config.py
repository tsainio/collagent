"""
CollAgent - Configuration Management

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import os
from pathlib import Path
from typing import Optional

import yaml

# Cache for loaded configuration
_config_cache: Optional[dict] = None


def load_config() -> dict:
    """Load and cache the models.yaml configuration file."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_path = Path(__file__).parent / "models.yaml"
    with open(config_path, "r") as f:
        _config_cache = yaml.safe_load(f)

    return _config_cache


def get_models() -> list:
    """Return all model configurations."""
    config = load_config()
    return config.get("models", [])


def get_model_by_id(model_id: str) -> Optional[dict]:
    """Look up a model configuration by its ID."""
    for model in get_models():
        if model.get("id") == model_id:
            return model
    return None


def get_default_model() -> dict:
    """Get the default model configuration."""
    for model in get_models():
        if model.get("default"):
            return model
    # Fall back to first model if no default specified
    models = get_models()
    return models[0] if models else {}


def get_provider_config(provider: str) -> dict:
    """Get provider configuration by name."""
    config = load_config()
    return config.get("providers", {}).get(provider, {})


def get_available_models() -> list:
    """
    Return models whose provider API key is set in the environment.

    This filters models to only those that can actually be used,
    based on whether the required API key environment variable is set.
    """
    available = []
    for model in get_models():
        provider = model.get("provider")
        provider_config = get_provider_config(provider)
        env_key = provider_config.get("env_key")
        if env_key and os.environ.get(env_key):
            available.append(model)
    return available


def get_model_ids() -> list:
    """Return a list of all model IDs."""
    return [m.get("id") for m in get_models()]


def get_available_model_ids() -> list:
    """Return a list of available model IDs (those with API keys set)."""
    return [m.get("id") for m in get_available_models()]
