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
        """Launch all subs as Windows Terminal split panes.

        Uses sequential wt.exe calls for reliability.

        Layouts (orchestrator is always top-left):
          1 sub:  [orch  | sub1 ]

          2 subs: [orch  | sub1 ]
                  [      | sub2 ]

          3 subs: [orch  | sub1 ]   (2x2 grid)
                  [sub3  | sub2 ]

          4+ subs: [orch  | sub1 ]
                   [sub4  | sub2 ]
                   [      | sub3 ]
        """
        n = len(models)

        if n == 1:
            # [orch | sub1]
            self._wt_split("-V", models[0], run_dir)

        elif n == 2:
            # Split right: [orch | sub1]
            self._wt_split("-V", models[0], run_dir)
            time.sleep(1)
            # Split sub1 down: [orch | sub1]
            #                  [     | sub2]
            self._wt_split("-H", models[1], run_dir)

        elif n == 3:
            # Step 1: split down: [orch] / [sub1], focus moves to sub1 (bottom)
            self._wt_split("-H", models[0], run_dir)
            time.sleep(1)
            # Step 2: split sub1 right: [orch] / [sub1 | sub2], focus on sub2
            self._wt_split("-V", models[1], run_dir)
            time.sleep(1)
            # Step 3: move focus up to orch
            self._wt_action("move-focus", "--direction", "up")
            time.sleep(0.5)
            # Step 4: split orch right: [orch | sub3] / [sub1 | sub2]
            self._wt_split("-V", models[2], run_dir)

        else:
            # 4+ subs: right column stacked
            self._wt_split("-V", models[0], run_dir)
            for i in range(1, n):
                time.sleep(1)
                self._wt_split("-H", models[i], run_dir)

    def _wt_action(self, *args: str) -> None:
        """Run a single wt.exe action (e.g., move-focus)."""
        cmd = ["wt.exe", "-w", "0"] + list(args)
        subprocess.Popen(cmd)

    def _wt_split(self, direction: str, model: str, run_dir: Path) -> None:
        """Run a single wt.exe split-pane command."""
        sub_dir = run_dir / f"sub-{model}"
        pane_cmd = self._build_pane_cmd(model, sub_dir)
        cmd = [
            "wt.exe", "-w", "0",
            "split-pane", direction, "--size", "0.5",
            "--title", f"sub-{model}",
            "cmd", "/k", pane_cmd,
        ]
        subprocess.Popen(cmd)

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
