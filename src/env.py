"""Environment sanitization for launching Claude Code subprocesses.

When launching claude CLI as a subprocess, we must sanitize the environment
to avoid inheriting Vertex AI settings from the parent process. For non-Claude
models, we set ANTHROPIC_BASE_URL to point to the LiteLLM proxy.
"""

import os

# Env vars that force Vertex AI backend and must be cleared
VERTEX_VARS = [
    "CLAUDE_CODE_USE_VERTEX",
    "ANTHROPIC_VERTEX_PROJECT_ID",
    "ANTHROPIC_VERTEX_REGION",
]

# Env vars that indicate we're inside a Claude Code session
CLAUDE_SESSION_VARS = [
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
]


def build_env(*, litellm_url: str | None = None, litellm_key: str | None = None) -> dict:
    """Build a sanitized environment dict for a Claude Code subprocess.

    Args:
        litellm_url: If set, configures ANTHROPIC_BASE_URL for LiteLLM proxy routing.
        litellm_key: API key for the LiteLLM proxy.

    Returns:
        A copy of os.environ with Vertex/session vars cleared and LiteLLM vars set.
    """
    env = os.environ.copy()

    # Clear vars that would force Vertex backend or confuse nested sessions
    for var in VERTEX_VARS + CLAUDE_SESSION_VARS:
        env.pop(var, None)

    # Set LiteLLM proxy vars for non-Claude models
    if litellm_url:
        env["ANTHROPIC_BASE_URL"] = litellm_url
    if litellm_key:
        env["ANTHROPIC_API_KEY"] = litellm_key

    return env


def build_cmd_env_string(*, litellm_url: str | None = None, litellm_key: str | None = None) -> list[str]:
    """Build cmd.exe 'set' commands to sanitize env inside a WT pane.

    Returns a list of 'set VAR=value' strings to chain with &&.
    """
    parts = []

    # Clear Vertex and session vars (set VAR= clears it in cmd.exe)
    for var in VERTEX_VARS + CLAUDE_SESSION_VARS:
        parts.append(f"set {var}=")

    # For LiteLLM models: use AUTH_TOKEN (not API_KEY) to avoid conflict
    # Clear API_KEY so Claude Code doesn't see both
    if litellm_url:
        parts.append(f"set ANTHROPIC_BASE_URL={litellm_url}")
        parts.append("set ANTHROPIC_API_KEY=")
    if litellm_key:
        parts.append(f"set ANTHROPIC_AUTH_TOKEN={litellm_key}")

    return parts


def build_bash_env_string(*, litellm_url: str | None = None, litellm_key: str | None = None) -> list[str]:
    """Build bash 'export/unset' commands to sanitize env inside a tmux pane.

    Returns a list of shell commands.
    """
    parts = []

    # Clear Vertex and session vars
    for var in VERTEX_VARS + CLAUDE_SESSION_VARS:
        parts.append(f"unset {var}")

    # For LiteLLM models: use AUTH_TOKEN (not API_KEY) to avoid conflict
    if litellm_url:
        parts.append(f"export ANTHROPIC_BASE_URL={litellm_url}")
        parts.append("unset ANTHROPIC_API_KEY")
    if litellm_key:
        parts.append(f"export ANTHROPIC_AUTH_TOKEN={litellm_key}")

    return parts
