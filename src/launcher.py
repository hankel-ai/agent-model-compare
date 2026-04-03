"""Launch Claude Code sessions in Windows Terminal split panes."""

import subprocess
import time
from pathlib import Path

from .config import get_litellm_config, is_claude_model
from .env import build_cmd_env_string


class PaneLauncher:
    def __init__(self, config: dict):
        self.config = config

    def launch_subs(self, run_dir: Path, models: list[str]) -> None:
        """Launch each sub as a Windows Terminal split pane.

        Creates one pane per model, each running an interactive Claude Code session
        in the model's workspace directory.
        """
        for i, model in enumerate(models):
            sub_dir = run_dir / f"sub-{model}"
            cmd_string = self._build_pane_cmd(model, sub_dir)

            # Alternate horizontal and vertical splits for a grid layout
            split = "-H" if i % 2 == 0 else "-V"
            title = f"sub-{model}"

            wt_args = [
                "wt.exe", "-w", "0",
                "split-pane", split,
                "--title", title,
                "cmd", "/k", cmd_string,
            ]

            subprocess.Popen(wt_args)
            time.sleep(1.5)  # Let WT settle between pane launches

    def _build_pane_cmd(self, model: str, workspace: Path) -> str:
        """Build the cmd.exe command string for a sub's pane.

        For Claude models: clears Vertex vars, launches claude directly.
        For non-Claude models: sets ANTHROPIC_BASE_URL to LiteLLM proxy.
        """
        litellm_url = None
        litellm_key = None

        if not is_claude_model(model, self.config):
            litellm = get_litellm_config(self.config)
            litellm_url = litellm.get("url")
            litellm_key = litellm.get("key")

        parts = build_cmd_env_string(litellm_url=litellm_url, litellm_key=litellm_key)

        # cd to workspace and launch claude
        parts.append(f"cd /d {workspace}")
        parts.append(f"claude --model {model} --dangerously-skip-permissions")

        return " && ".join(parts)
