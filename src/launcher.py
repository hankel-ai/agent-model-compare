"""Launch Claude Code sessions in Windows Terminal split panes."""

import subprocess
import time
from pathlib import Path

from .config import get_litellm_config, is_claude_model
from .env import build_cmd_env_string


INITIAL_PROMPT = "Read the CLAUDE.md file in this directory and complete the task described there. Start working immediately."


class PaneLauncher:
    def __init__(self, config: dict):
        self.config = config

    def launch_subs(self, run_dir: Path, models: list[str]) -> None:
        """Launch all subs as Windows Terminal split panes in a single command.

        Layouts (orchestrator is always top-left):
          1 sub:  [orch  | sub1 ]

          2 subs: [orch  | sub1 ]
                  [      | sub2 ]

          3 subs: [orch  | sub1 ]   (2x2 grid)
                  [sub3  | sub2 ]

          4 subs: [orch  | sub1 ]
                  [sub4  | sub2 ]
                  [      | sub3 ]
        """
        # Build one chained wt command for the entire layout
        wt_parts = self._build_wt_command(run_dir, models)
        cmd = " ".join(wt_parts)
        subprocess.Popen(cmd, shell=True)

    def _build_wt_command(self, run_dir: Path, models: list[str]) -> list[str]:
        """Build a single wt.exe command that creates the full pane layout.

        Uses \\; to chain split-pane and move-focus commands.
        """
        n = len(models)
        parts = ["wt.exe", "-w", "0"]

        if n == 1:
            # [orch | sub1]
            parts += self._split_cmd("-V", models[0], run_dir)

        elif n == 2:
            # Split right: [orch | sub1], focus=sub1
            parts += self._split_cmd("-V", models[0], run_dir)
            # Split sub1 down: [orch | sub1], focus=sub2
            #                  [     | sub2]
            parts += ["\\;"] + self._split_cmd("-H", models[1], run_dir)

        elif n == 3:
            # Step 1: split down: [orch] / [sub1], focus=sub1 (bottom)
            parts += self._split_cmd("-H", models[0], run_dir)
            # Step 2: split sub1 right: [orch] / [sub1 | sub2], focus=sub2
            parts += ["\\;"] + self._split_cmd("-V", models[1], run_dir)
            # Step 3: move focus up to orch
            parts += ["\\;", "move-focus", "--direction", "up"]
            # Step 4: split orch right: [orch | sub3] / [sub1 | sub2], focus=sub3
            parts += ["\\;"] + self._split_cmd("-V", models[2], run_dir)

        else:
            # 4+ subs: right column gets multiple, left column for overflow
            # Start: split right for sub1
            parts += self._split_cmd("-V", models[0], run_dir)
            # Stack remaining in right column first
            for i in range(1, n):
                parts += ["\\;"] + self._split_cmd("-H", models[i], run_dir)

        return parts

    def _split_cmd(self, direction: str, model: str, run_dir: Path) -> list[str]:
        """Build the split-pane portion for one sub."""
        sub_dir = run_dir / f"sub-{model}"
        pane_cmd = self._build_pane_cmd(model, sub_dir)
        return [
            "split-pane", direction, "--size", "0.5",
            "--title", f"sub-{model}",
            "cmd", "/k", f'"{pane_cmd}"',
        ]

    def _build_pane_cmd(self, model: str, workspace: Path) -> str:
        """Build the cmd.exe command string for a sub's pane."""
        litellm_url = None
        litellm_key = None

        if not is_claude_model(model, self.config):
            litellm = get_litellm_config(self.config)
            litellm_url = litellm.get("url")
            litellm_key = litellm.get("key")

        parts = build_cmd_env_string(litellm_url=litellm_url, litellm_key=litellm_key)

        # cd to workspace and launch claude with initial prompt
        parts.append(f"cd /d {workspace}")
        parts.append(f'claude --model {model} --dangerously-skip-permissions {INITIAL_PROMPT}')

        return " && ".join(parts)
