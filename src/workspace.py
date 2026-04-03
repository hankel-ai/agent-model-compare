"""Workspace management — create run directories and CLAUDE.md per sub."""

import json
from datetime import datetime
from pathlib import Path

WORKSPACES_DIR = Path(__file__).parent.parent / "workspaces"

CLAUDE_MD_TEMPLATE = """# Task

{task}

# Rules

- Work ONLY within this directory. Do not access parent directories.
- Write all code, tests, and output files here.
- At key milestones, update `progress.json` with:
  ```json
  {{"step": 1, "total": 5, "status": "in_progress", "message": "description"}}
  ```
- When completely done, create `DONE.md` with a summary:
  - What you built
  - How to run it
  - How to test it
  - Any issues or limitations
- Do NOT modify or delete this CLAUDE.md file.
"""


class WorkspaceManager:
    def __init__(self, base: Path = WORKSPACES_DIR):
        self.base = base

    def create_run(self, task: str, models: list[str], name: str | None = None) -> Path:
        """Create a run directory with per-model subdirectories and CLAUDE.md files.

        Returns the run directory path.
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_name = f"{name}-{timestamp}" if name else timestamp
        run_dir = self.base / f"run-{run_name}"
        run_dir.mkdir(parents=True)

        # Save run config
        config = {
            "task": task,
            "models": models,
            "created": timestamp,
            "run_name": run_name,
        }
        (run_dir / "config.json").write_text(json.dumps(config, indent=2))

        # Create per-model workspaces
        for model in models:
            sub_dir = run_dir / f"sub-{model}"
            sub_dir.mkdir()
            claude_md = CLAUDE_MD_TEMPLATE.format(task=task)
            (sub_dir / "CLAUDE.md").write_text(claude_md)

        return run_dir

    def get_sub_dir(self, run_dir: Path, model: str) -> Path:
        return run_dir / f"sub-{model}"

    def list_runs(self) -> list[Path]:
        """List all run directories, newest first."""
        if not self.base.exists():
            return []
        runs = sorted(self.base.glob("run-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        return runs

    def find_run(self, name: str) -> Path | None:
        """Find a run directory by name (partial match)."""
        for run_dir in self.list_runs():
            if name in run_dir.name:
                return run_dir
        return None

    def load_run_config(self, run_dir: Path) -> dict:
        """Load the config.json from a run directory."""
        config_path = run_dir / "config.json"
        if config_path.exists():
            return json.loads(config_path.read_text())
        return {}
