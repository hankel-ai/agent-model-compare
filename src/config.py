"""Load and parse models.yaml configuration."""

import os
from pathlib import Path

import yaml

ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.is_file():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load the models.yaml config file."""
    with open(path) as f:
        return yaml.safe_load(f)


def is_claude_model(model: str, config: dict) -> bool:
    """Check if a model name is a native Claude model (direct Anthropic API)."""
    return model in config.get("claude_models", [])


def get_litellm_config(config: dict) -> dict:
    """Get LiteLLM proxy config.

    Reads ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN from config.yaml.
    AUTH_TOKEN falls back to LITELLM_MASTER_KEY from .env if not set in config.
    """
    litellm = config.get("litellm", {})
    url = litellm.get("ANTHROPIC_BASE_URL", "http://localhost:4000")
    key = litellm.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("LITELLM_MASTER_KEY", "")
    return {"url": url, "key": key}


CONFIG_DIR = DEFAULT_CONFIG_PATH.parent


def get_extra_env(config: dict) -> dict[str, str]:
    """Get extra environment variables from config.

    Values that match a file in the config/ directory are resolved to full paths.
    """
    env = {}
    for key, val in config.get("env", {}).items():
        val = str(val)
        candidate = CONFIG_DIR / val
        if candidate.is_file():
            val = str(candidate.resolve())
        env[key] = val
    return env
