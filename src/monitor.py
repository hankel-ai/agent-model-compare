"""Monitor workspaces for progress and completion."""

import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.table import Table


class WorkspaceMonitor:
    def __init__(self, run_dir: Path, models: list[str]):
        self.run_dir = run_dir
        self.models = models

    def get_status(self) -> dict:
        """Check progress of all subs by reading their workspace files."""
        status = {}
        for model in self.models:
            sub_dir = self.run_dir / f"sub-{model}"
            done_file = sub_dir / "DONE.md"
            progress_file = sub_dir / "progress.json"

            if done_file.exists():
                status[model] = {
                    "status": "completed",
                    "message": "Done",
                }
            elif progress_file.exists():
                try:
                    progress = json.loads(progress_file.read_text())
                    prog_status = progress.get("status", "in_progress")
                    if prog_status == "completed":
                        status[model] = {
                            "status": "completed",
                            "message": progress.get("message", "Done"),
                        }
                    else:
                        status[model] = {
                            "status": "in_progress",
                            "step": progress.get("step", "?"),
                            "total": progress.get("total", "?"),
                            "message": progress.get("message", ""),
                        }
                except (json.JSONDecodeError, OSError):
                    status[model] = {"status": "in_progress", "message": "reading progress..."}
            else:
                # Check if sub has created any files beyond CLAUDE.md
                files = [f for f in sub_dir.iterdir() if f.name != "CLAUDE.md"] if sub_dir.exists() else []
                if files:
                    status[model] = {"status": "working", "message": f"{len(files)} files", "files": len(files)}
                else:
                    status[model] = {"status": "waiting", "message": ""}

        return status

    def all_done(self) -> bool:
        return all(s["status"] == "completed" for s in self.get_status().values())

    def _build_table(self) -> Table:
        """Build a rich Table showing current status of all subs."""
        table = Table(title=f"Run: {self.run_dir.name}", show_lines=False)
        table.add_column("Model", style="cyan", min_width=15)
        table.add_column("Status", min_width=12)
        table.add_column("Progress", min_width=10)
        table.add_column("Message", min_width=30)

        status = self.get_status()
        for model in self.models:
            info = status.get(model, {"status": "unknown"})
            st = info["status"]

            if st == "completed":
                status_str = "[bold green]Done[/bold green]"
                progress_str = "[green]complete[/green]"
            elif st == "in_progress":
                step = info.get("step", "?")
                total = info.get("total", "?")
                status_str = "[yellow]in progress[/yellow]"
                progress_str = f"{step}/{total}"
            elif st == "working":
                status_str = "[yellow]working[/yellow]"
                progress_str = f'{info.get("files", 0)} files'
            else:
                status_str = "[dim]waiting[/dim]"
                progress_str = ""

            table.add_row(model, status_str, progress_str, info.get("message", ""))

        return table

    def watch(self, interval: int = 10) -> None:
        """Display live status updates until all subs complete or user interrupts."""
        console = Console()
        console.print(f"\n[bold]Monitoring[/bold] {self.run_dir.name}")
        if sys.platform == "win32":
            pane_hint = "Switch panes with Alt+Arrow to interact with subs."
        else:
            pane_hint = "Switch tmux panes with Ctrl+B then arrow keys to interact with subs."
        console.print(f"[dim]{pane_hint} Ctrl+C to stop monitoring.[/dim]\n")

        try:
            with Live(self._build_table(), console=console, refresh_per_second=0.2) as live:
                while not self.all_done():
                    time.sleep(interval)
                    live.update(self._build_table())
                # Final update
                live.update(self._build_table())

            console.print("\n[bold green]All subs completed![/bold green]")
            console.print(f"Run [cyan]python -m src.cli report --run {self.run_dir.name}[/cyan] to generate the comparison report.\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped. Subs are still running in their panes.[/yellow]")
            console.print(f"Resume monitoring: [cyan]python -m src.cli status --run {self.run_dir.name}[/cyan]\n")
