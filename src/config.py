"""Load and parse config.yaml configuration."""

import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

# Auto-load .env at import time so subsequent os.environ.get() calls see it.
if ENV_FILE.is_file():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load the config.yaml file."""
    with open(path) as f:
        return yaml.safe_load(f)


def is_claude_model(model: str, config: dict) -> bool:
    """Check if a model name is a native Claude model (direct Anthropic API)."""
    return model in config.get("claude_models", [])


def get_litellm_config(config: dict | None = None) -> dict:
    """Get LiteLLM proxy config from environment.

    Reads LITELLM_BASE_URL and LITELLM_MASTER_KEY from .env / environment.
    Returns empty strings if unset — caller treats that as "no LiteLLM available".
    The `config` argument is accepted for backward compatibility but unused.
    """
    return {
        "url": os.environ.get("LITELLM_BASE_URL", "").strip(),
        "key": os.environ.get("LITELLM_MASTER_KEY", "").strip(),
    }


# Env vars that get injected into agent subprocesses if set in .env
PASSTHROUGH_ENV_VARS = ("HTTPS_PROXY", "HTTP_PROXY", "NODE_EXTRA_CA_CERTS")


def get_extra_env(config: dict | None = None) -> dict[str, str]:
    """Get extra environment variables to inject into agent subprocesses.

    Reads from .env / environment. Skips any variable that is unset or empty.
    For NODE_EXTRA_CA_CERTS, resolves a relative path against the project root.
    The `config` argument is accepted for backward compatibility but unused.
    """
    env = {}
    for var in PASSTHROUGH_ENV_VARS:
        val = os.environ.get(var, "").strip()
        if not val:
            continue
        if var == "NODE_EXTRA_CA_CERTS":
            candidate = Path(val)
            if not candidate.is_absolute():
                candidate = (PROJECT_ROOT / val).resolve()
            if candidate.is_file():
                val = str(candidate)
        env[var] = val
    return env
