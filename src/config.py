"""Load and parse models.yaml configuration."""

from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "models.yaml"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load the models.yaml config file."""
    with open(path) as f:
        return yaml.safe_load(f)


def is_claude_model(model: str, config: dict) -> bool:
    """Check if a model name is a native Claude model (direct Anthropic API)."""
    return model in config.get("claude_models", [])


def get_litellm_config(config: dict) -> dict:
    """Get LiteLLM proxy URL and key from config."""
    return config.get("litellm", {"url": "http://localhost:4000", "key": ""})
