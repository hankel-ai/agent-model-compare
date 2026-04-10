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


# Env vars that should NOT be passed into Docker sandboxes — the sandbox has
# its own proxy, and host filesystem paths don't exist inside the container.
_SANDBOX_EXCLUDED_VARS = {"HTTPS_PROXY", "HTTP_PROXY", "NODE_EXTRA_CA_CERTS"}


def build_docker_env_flags(
    *,
    litellm_url: str | None = None,
    litellm_key: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> list[str]:
    """Build '-e KEY=VAL' flags for docker sandbox exec.

    Returns a list of strings like ['-e', 'ANTHROPIC_BASE_URL=http://...', ...].
    Excludes proxy/cert vars that conflict with sandbox networking.
    """
    parts = []

    if litellm_url:
        parts.extend(["-e", f"ANTHROPIC_BASE_URL={litellm_url}"])
        parts.extend(["-e", "ANTHROPIC_API_KEY="])
    if litellm_key:
        parts.extend(["-e", f"ANTHROPIC_AUTH_TOKEN={litellm_key}"])

    if extra_env:
        for key, val in extra_env.items():
            if key in _SANDBOX_EXCLUDED_VARS:
                continue
            parts.extend(["-e", f"{key}={val}"])

    return parts
