"""Launch Claude Code sessions in Windows Terminal panes or tmux panes."""

import subprocess
import sys
import time
from pathlib import Path

from .config import get_extra_env, get_litellm_config, is_claude_model
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

        extra_env = get_extra_env(self.config)
        env_parts = build_cmd_env_string(litellm_url=litellm_url, litellm_key=litellm_key, extra_env=extra_env)

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
        """Launch subs as tmux panes or windows inside a new tmux session.

        1-3 models: split panes in a single window (monitor + agents visible).
        4+ models: each agent gets its own tmux window (tab). Window 0 = monitor.

        Pane layouts (1-3 models):
          1 sub:  [orch  | sub1 ]

          2 subs: [orch  | sub1 ]
                  [      | sub2 ]

          3 subs: [orch  | sub1 ]   (2x2 grid)
                  [sub3  | sub2 ]
        """
        for model in models:
            self._write_start_sh(run_dir, model)

        session = run_dir.name
        n = len(models)

        # Create a new tmux session (detached). Window 0 is the orchestrator.
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session, "-x", "200", "-y", "50"],
            check=True,
        )

        if n <= 3:
            # Pane layout for small runs
            if n == 1:
                self._tmux_split(session, "-h", models[0], run_dir)
            elif n == 2:
                self._tmux_split(session, "-h", models[0], run_dir)
                time.sleep(0.2)
                self._tmux_split(session, "-v", models[1], run_dir, target_pane=1)
            elif n == 3:
                self._tmux_split(session, "-v", models[0], run_dir)
                time.sleep(0.2)
                self._tmux_split(session, "-h", models[1], run_dir, target_pane=1)
                time.sleep(0.2)
                self._tmux_split(session, "-h", models[2], run_dir, target_pane=0)
            # Lock the panes into a tiled grid so they don't drift when sub
            # TUIs start up and trigger resize events.
            time.sleep(0.2)
            subprocess.run(
                ["tmux", "select-layout", "-t", f"{session}:0", "tiled"],
                check=True,
            )
        else:
            # Window (tab) layout for 4+ models
            for model in models:
                script = run_dir / f"sub-{model}" / "_start.sh"
                subprocess.run(
                    ["tmux", "new-window", "-t", session, "-n", model, str(script)],
                    check=True,
                )
            # Go back to window 0 (monitor)
            subprocess.run(
                ["tmux", "select-window", "-t", f"{session}:0"],
                check=True,
            )

        # Configure status bar with shortcuts help
        self._configure_tmux_status(session, n)

        # Run the status monitor in window 0, pane 0
        project_root = run_dir.parent.parent
        monitor_cmd = f'cd "{project_root}" && python3 -m src.cli status --run {run_dir.name} -w'
        subprocess.run(
            ["tmux", "send-keys", "-t", f"{session}:0.0", monitor_cmd, "Enter"],
            check=True,
        )

        # Attach to the session
        subprocess.run(["tmux", "attach-session", "-t", session])

    def _configure_tmux_status(self, session: str, n: int) -> None:
        """Set tmux status bar to show navigation shortcuts."""
        if n <= 3:
            shortcuts = "Alt+arrows or click:switch pane | ^B+z:zoom | ^C:stop monitor"
        else:
            shortcuts = "Alt+Left/Right or click:prev/next tab | ^B+z:zoom | ^C:stop monitor"

        tmux_opts = [
            ("status", "on"),
            ("status-style", "bg=colour235,fg=colour248"),
            ("status-left", f" [{session[:20]}] "),
            ("status-left-length", "25"),
            ("status-right", f" {shortcuts} "),
            ("status-right-length", "90"),
            ("window-status-current-style", "bg=colour39,fg=colour232,bold"),
            ("window-status-format", " #I:#W "),
            ("window-status-current-format", " #I:#W "),
            # Click-to-focus panes / click-on-status to switch windows.
            ("mouse", "on"),
            # Each pane uses its full size when active rather than being
            # constrained by other clients — fewer redraw glitches when the
            # monitor table refreshes alongside the sub TUIs.
            ("aggressive-resize", "on"),
        ]
        for opt, val in tmux_opts:
            subprocess.run(
                ["tmux", "set-option", "-t", session, opt, val],
                check=True,
            )

        # Prefix-free keybindings: Alt+Arrow to navigate without ^B.
        # In pane mode (n<=3) all four arrows move between panes.
        # In window mode (n>=4) Left/Right step through tabs; Up/Down are
        # left unbound since each tab is a single full-window pane.
        if n <= 3:
            keybinds = [
                ("M-Left", "select-pane -L"),
                ("M-Right", "select-pane -R"),
                ("M-Up", "select-pane -U"),
                ("M-Down", "select-pane -D"),
            ]
        else:
            keybinds = [
                ("M-Left", "previous-window"),
                ("M-Right", "next-window"),
            ]
        for key, cmd in keybinds:
            subprocess.run(
                ["tmux", "bind-key", "-n", "-T", "root", key, cmd],
                check=True,
            )

    def _write_start_sh(self, run_dir: Path, model: str) -> Path:
        """Write a _start.sh bash script for a sub."""
        sub_dir = run_dir / f"sub-{model}"

        litellm_url = None
        litellm_key = None
        if not is_claude_model(model, self.config):
            litellm = get_litellm_config(self.config)
            litellm_url = litellm.get("url")
            litellm_key = litellm.get("key")

        extra_env = get_extra_env(self.config)
        env_parts = build_bash_env_string(litellm_url=litellm_url, litellm_key=litellm_key, extra_env=extra_env)

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
