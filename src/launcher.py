"""Launch Claude Code sessions in Windows Terminal panes or tmux panes."""

import subprocess
import sys
import time
from pathlib import Path

from .config import get_litellm_config, is_claude_model
from .env import build_bash_env_string, build_cmd_env_string


INITIAL_PROMPT = "Read the CLAUDE.md file in this directory and complete the task described there. Start working immediately."


def is_windows() -> bool:
    return sys.platform == "win32"


class PaneLauncher:
    def __init__(self, config: dict):
        self.config = config

    def launch_subs(self, run_dir: Path, models: list[str]) -> bool:
        """Launch all subs as split panes (WT on Windows, tmux on Linux/macOS).

        Returns True if monitoring is handled internally (tmux runs it in pane 0).
        Returns False if the caller should run the monitor (Windows Terminal).
        """
        if is_windows():
            self._launch_wt(run_dir, models)
            return False
        else:
            self._launch_tmux(run_dir, models)
            return True

    # ── Windows Terminal ─────────────────────────────────────────────────

    def _launch_wt(self, run_dir: Path, models: list[str]) -> None:
        """Launch subs as Windows Terminal split panes.

        Writes a _start.cmd batch file per sub to avoid quoting issues,
        then uses sequential wt.exe calls to build the pane layout.

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
        for model in models:
            self._write_start_cmd(run_dir, model)

        n = len(models)

        if n == 1:
            self._wt_split("-V", models[0], run_dir)

        elif n == 2:
            self._wt_split("-V", models[0], run_dir)
            time.sleep(1)
            self._wt_split("-H", models[1], run_dir)

        elif n == 3:
            self._wt_split("-H", models[0], run_dir)
            time.sleep(1)
            self._wt_split("-V", models[1], run_dir)
            time.sleep(1)
            self._wt_action("move-focus", "--direction", "up")
            time.sleep(0.5)
            self._wt_split("-V", models[2], run_dir)

        else:
            self._wt_split("-V", models[0], run_dir)
            for i in range(1, n):
                time.sleep(1)
                self._wt_split("-H", models[i], run_dir)

    def _write_start_cmd(self, run_dir: Path, model: str) -> Path:
        """Write a _start.cmd batch file for a sub."""
        sub_dir = run_dir / f"sub-{model}"

        litellm_url = None
        litellm_key = None
        if not is_claude_model(model, self.config):
            litellm = get_litellm_config(self.config)
            litellm_url = litellm.get("url")
            litellm_key = litellm.get("key")

        env_parts = build_cmd_env_string(litellm_url=litellm_url, litellm_key=litellm_key)

        lines = ["@echo off"]
        for part in env_parts:
            lines.append(part)
        lines.append(f"cd /d {sub_dir}")
        lines.append(f'claude --model {model} --dangerously-skip-permissions "{INITIAL_PROMPT}"')

        script_path = sub_dir / "_start.cmd"
        script_path.write_text("\r\n".join(lines) + "\r\n")
        return script_path

    def _wt_action(self, *args: str) -> None:
        """Run a single wt.exe action (e.g., move-focus)."""
        cmd = "wt.exe -w 0 " + " ".join(args)
        subprocess.Popen(cmd, shell=True)

    def _wt_split(self, direction: str, model: str, run_dir: Path) -> None:
        """Run a single wt.exe split-pane command."""
        sub_dir = run_dir / f"sub-{model}"
        script = sub_dir / "_start.cmd"
        cmd = (
            f'wt.exe -w 0 split-pane {direction} --size 0.5'
            f' --title sub-{model}'
            f' cmd /k "{script}"'
        )
        subprocess.Popen(cmd, shell=True)

    # ── tmux (Linux / macOS) ─────────────────────────────────────────────

    def _launch_tmux(self, run_dir: Path, models: list[str]) -> None:
        """Launch subs as tmux split panes inside a new tmux session.

        Creates a tmux session named after the run, then splits panes
        for each model. The first pane is the orchestrator (monitor),
        and each sub gets its own pane running a bash start script.

        Layouts mirror the WT version:
          1 sub:  [orch  | sub1 ]

          2 subs: [orch  | sub1 ]
                  [      | sub2 ]

          3 subs: [orch  | sub1 ]   (2x2 grid)
                  [sub3  | sub2 ]

          4+ subs: [orch  | sub1 ]
                   [sub4  | sub2 ]
                   [      | sub3 ]
        """
        for model in models:
            self._write_start_sh(run_dir, model)

        session = run_dir.name
        n = len(models)

        # Create a new tmux session (detached). Pane 0 is the orchestrator.
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session, "-x", "200", "-y", "50"],
            check=True,
        )

        if n == 1:
            self._tmux_split(session, "-h", models[0], run_dir)

        elif n == 2:
            # Split right for sub1
            self._tmux_split(session, "-h", models[0], run_dir)
            # Split sub1 pane down for sub2
            self._tmux_split(session, "-v", models[1], run_dir, target_pane=1)

        elif n == 3:
            # Split down for sub1
            self._tmux_split(session, "-v", models[0], run_dir)
            # Split sub1 right for sub2
            self._tmux_split(session, "-h", models[1], run_dir, target_pane=1)
            # Select orchestrator pane (0), split right for sub3
            self._tmux_split(session, "-h", models[2], run_dir, target_pane=0)

        else:
            # First sub goes right
            self._tmux_split(session, "-h", models[0], run_dir)
            for i in range(1, n):
                # Stack remaining subs vertically in the right column
                self._tmux_split(session, "-v", models[i], run_dir, target_pane=1)

        # Run the status monitor in pane 0 (orchestrator pane)
        project_root = run_dir.parent.parent
        monitor_cmd = f'cd "{project_root}" && python3 -m src.cli status --run {run_dir.name} -w'
        subprocess.run(
            ["tmux", "send-keys", "-t", f"{session}:0.0", monitor_cmd, "Enter"],
            check=True,
        )

        # Attach to the session
        subprocess.run(["tmux", "attach-session", "-t", session])

    def _write_start_sh(self, run_dir: Path, model: str) -> Path:
        """Write a _start.sh bash script for a sub."""
        sub_dir = run_dir / f"sub-{model}"

        litellm_url = None
        litellm_key = None
        if not is_claude_model(model, self.config):
            litellm = get_litellm_config(self.config)
            litellm_url = litellm.get("url")
            litellm_key = litellm.get("key")

        env_parts = build_bash_env_string(litellm_url=litellm_url, litellm_key=litellm_key)

        lines = ["#!/usr/bin/env bash", "set -e"]
        lines.extend(env_parts)
        lines.append(f'cd "{sub_dir}"')
        lines.append(f'claude --model {model} --dangerously-skip-permissions "{INITIAL_PROMPT}"')

        script_path = sub_dir / "_start.sh"
        script_path.write_text("\n".join(lines) + "\n")
        script_path.chmod(0o755)
        return script_path

    def _tmux_split(
        self,
        session: str,
        direction: str,
        model: str,
        run_dir: Path,
        target_pane: int | None = None,
    ) -> None:
        """Split a tmux pane and run the sub's start script in it."""
        sub_dir = run_dir / f"sub-{model}"
        script = sub_dir / "_start.sh"

        if target_pane is not None:
            target = f"{session}:0.{target_pane}"
        else:
            target = f"{session}:0"
        cmd = ["tmux", "split-window", direction, "-t", target, str(script)]

        subprocess.run(cmd, check=True)
