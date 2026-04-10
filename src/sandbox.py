"""Docker sandbox lifecycle management for isolated agent execution."""

import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


# Private RFC-1918 ranges and their CIDR blocks
_PRIVATE_CIDRS = [
    ("192.168.", "192.168.0.0/16"),
    ("10.", "10.0.0.0/8"),
    ("172.16.", "172.16.0.0/12"),
    ("172.17.", "172.16.0.0/12"),
    ("172.18.", "172.16.0.0/12"),
    ("172.19.", "172.16.0.0/12"),
    ("172.20.", "172.16.0.0/12"),
    ("172.21.", "172.16.0.0/12"),
    ("172.22.", "172.16.0.0/12"),
    ("172.23.", "172.16.0.0/12"),
    ("172.24.", "172.16.0.0/12"),
    ("172.25.", "172.16.0.0/12"),
    ("172.26.", "172.16.0.0/12"),
    ("172.27.", "172.16.0.0/12"),
    ("172.28.", "172.16.0.0/12"),
    ("172.29.", "172.16.0.0/12"),
    ("172.30.", "172.16.0.0/12"),
    ("172.31.", "172.16.0.0/12"),
]


def sandbox_name(run_name: str, model: str) -> str:
    """Generate a deterministic sandbox name for a model in a run."""
    return f"amc-{run_name}-{model}"


def create_sandbox(name: str, workspace_path: Path) -> None:
    """Create a Docker sandbox with the workspace mounted.

    Raises RuntimeError if Docker is not available or creation fails.
    """
    cmd = ["docker", "sandbox", "create", "claude", "--name", name, str(workspace_path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError(
            "Docker is not installed or not in PATH. "
            "Install Docker Desktop to use --sandbox mode."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to create sandbox '{name}': {e.stderr.strip()}"
        )


def _host_to_cidr(host: str) -> str | None:
    """Map a host IP to its private CIDR range. Returns None for localhost."""
    if host in ("localhost", "127.0.0.1", "::1"):
        return None
    for prefix, cidr in _PRIVATE_CIDRS:
        if host.startswith(prefix):
            return cidr
    return None


def configure_sandbox_network(name: str, litellm_url: str) -> None:
    """Configure sandbox network policy to allow LiteLLM proxy access.

    Parses the host from litellm_url and allows the corresponding private
    CIDR range. Prints a warning if the URL uses localhost.
    """
    from rich.console import Console
    console = Console()

    parsed = urlparse(litellm_url)
    host = parsed.hostname or ""

    if host in ("localhost", "127.0.0.1", "::1"):
        console.print(
            f"  [yellow]Warning:[/yellow] LITELLM_BASE_URL uses '{host}'. "
            "Sandbox mode requires your LAN IP (e.g., http://192.168.1.65:4000)."
        )
        return

    cidr = _host_to_cidr(host)
    if not cidr:
        console.print(
            f"  [yellow]Warning:[/yellow] Could not determine CIDR for host '{host}'. "
            "You may need to configure sandbox networking manually."
        )
        return

    cmd = [
        "docker", "sandbox", "network", "proxy", name,
        "--policy", "allow",
        "--allow-cidr", cidr,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        console.print(
            f"  [yellow]Warning:[/yellow] Failed to configure network for '{name}': "
            f"{e.stderr.strip()}"
        )


def stop_sandbox(name: str) -> bool:
    """Stop a Docker sandbox. Returns True if successful."""
    result = subprocess.run(
        ["docker", "sandbox", "stop", name],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def remove_sandbox(name: str) -> bool:
    """Remove a Docker sandbox. Returns True if successful."""
    result = subprocess.run(
        ["docker", "sandbox", "rm", name],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def cleanup_sandboxes(names: list[str]) -> int:
    """Stop and remove all sandboxes in the list. Returns count cleaned."""
    cleaned = 0
    for name in names:
        stop_sandbox(name)
        if remove_sandbox(name):
            cleaned += 1
    return cleaned
