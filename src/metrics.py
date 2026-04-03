"""Collect file-based metrics from completed workspaces."""

import os
from datetime import datetime
from pathlib import Path

# Extensions to count as code
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".sh", ".bash",
    ".html", ".css", ".scss", ".sql", ".yaml", ".yml", ".toml", ".json",
}

# Files to exclude from metrics
EXCLUDE_FILES = {"CLAUDE.md", "DONE.md", "progress.json"}


class MetricsCollector:
    def collect(self, sub_dir: Path, model: str) -> dict:
        """Collect metrics from a completed sub workspace."""
        all_files = [
            f for f in sub_dir.rglob("*")
            if f.is_file() and f.name not in EXCLUDE_FILES
        ]

        code_files = [f for f in all_files if f.suffix in CODE_EXTENSIONS]
        test_files = [f for f in code_files if "test" in f.name.lower() or f.name.startswith("test_")]

        loc = sum(self._count_lines(f) for f in code_files)
        test_loc = sum(self._count_lines(f) for f in test_files)

        done_file = sub_dir / "DONE.md"
        done_summary = done_file.read_text() if done_file.exists() else None

        # Completion time from DONE.md modification time
        done_time = None
        if done_file.exists():
            done_time = datetime.fromtimestamp(done_file.stat().st_mtime).isoformat()

        # Start time from CLAUDE.md (it's the oldest file, created at run start)
        claude_md = sub_dir / "CLAUDE.md"
        start_time = None
        if claude_md.exists():
            start_time = datetime.fromtimestamp(claude_md.stat().st_mtime).isoformat()

        return {
            "model": model,
            "files_created": len(all_files),
            "code_files": len(code_files),
            "test_files": len(test_files),
            "lines_of_code": loc,
            "test_lines": test_loc,
            "has_tests": len(test_files) > 0,
            "done_summary": done_summary,
            "start_time": start_time,
            "done_time": done_time,
        }

    def _count_lines(self, path: Path) -> int:
        try:
            return len(path.read_text(errors="ignore").splitlines())
        except OSError:
            return 0
