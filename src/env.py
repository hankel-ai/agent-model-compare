"""Environment configuration for launching Claude Code subprocesses.

Builds environment variables for agent subprocesses. For non-Claude models,
sets ANTHROPIC_BASE_URL to point to the LiteLLM proxy.
"""

import os


def build_env(
    *,
    litellm_url: str | None = None,
    litellm_key: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict:
    """Build an environment dict for a Claude Code subprocess.

    Args:
        litellm_url: If set, configures ANTHROPIC_BASE_URL for LiteLLM proxy routing.
        litellm_key: API key for the LiteLLM proxy.
        extra_env: Additional env vars from config to inject.

    Returns:
        A copy of os.environ with LiteLLM and extra vars applied.
    """
    env = os.environ.copy()

    if litellm_url:
        env["ANTHROPIC_BASE_URL"] = litellm_url
    if litellm_key:
        env["ANTHROPIC_API_KEY"] = litellm_key

    if extra_env:
        env.update(extra_env)

    return env


def build_cmd_env_string(
    *,
    litellm_url: str | None = None,
    litellm_key: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> list[str]:
    """Build cmd.exe 'set' commands for env inside a WT pane.

    Returns a list of 'set VAR=value' strings to chain with &&.
    """
    parts = []

    # For LiteLLM models: use AUTH_TOKEN (not API_KEY) to avoid conflict
    # Clear API_KEY so Claude Code doesn't see both
    if litellm_url:
        parts.append(f"set ANTHROPIC_BASE_URL={litellm_url}")
        parts.append("set ANTHROPIC_API_KEY=")
    if litellm_key:
        parts.append(f"set ANTHROPIC_AUTH_TOKEN={litellm_key}")

    if extra_env:
        for key, val in extra_env.items():
            parts.append(f"set {key}={val}")

    return parts


def build_bash_env_string(
    *,
    litellm_url: str | None = None,
    litellm_key: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> list[str]:
    """Build bash 'export' commands for env inside a tmux pane.

    Returns a list of shell commands.
    """
    parts = []

    # For LiteLLM models: use AUTH_TOKEN (not API_KEY) to avoid conflict
    if litellm_url:
        parts.append(f"export ANTHROPIC_BASE_URL={litellm_url}")
        parts.append("unset ANTHROPIC_API_KEY")
    if litellm_key:
        parts.append(f"export ANTHROPIC_AUTH_TOKEN={litellm_key}")

    if extra_env:
        for key, val in extra_env.items():
            parts.append(f"export {key}={val}")

    return parts
