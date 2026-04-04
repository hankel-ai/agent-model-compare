"""Validate sub workspaces by running tests and checking app launch."""

import subprocess
import sys
from pathlib import Path


class WorkspaceValidator:
    """Run tests and try launching apps in completed sub workspaces."""

    def validate(self, sub_dir: Path, model: str) -> dict:
        """Run all validations on a sub workspace.

        Returns dict with keys: tests_passed, tests_output, launch_ok, launch_output
        """
        result = {"model": model}

        # Install requirements if present
        req_file = sub_dir / "requirements.txt"
        if req_file.exists():
            self._pip_install(req_file)

        # Run tests
        test_result = self._run_tests(sub_dir)
        result.update(test_result)

        # Try launching the app
        launch_result = self._try_launch(sub_dir)
        result.update(launch_result)

        return result

    def _pip_install(self, req_file: Path) -> None:
        """Install requirements.txt (best effort, don't fail validation)."""
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)],
                capture_output=True, timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    def _run_tests(self, sub_dir: Path) -> dict:
        """Find and run test files. Returns test results."""
        test_files = list(sub_dir.rglob("test_*.py")) + list(sub_dir.rglob("*_test.py"))
        # Deduplicate
        test_files = list({str(f): f for f in test_files}.values())

        if not test_files:
            return {
                "tests_found": False,
                "tests_passed": None,
                "tests_output": "No test files found",
                "tests_total": 0,
                "tests_failures": 0,
            }

        # Make paths relative to sub_dir so they work with cwd
        rel_test_files = [str(f.relative_to(sub_dir)) for f in test_files]

        # Try pytest first, fall back to unittest
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "--tb=short", "-q"] + rel_test_files,
                capture_output=True, text=True, timeout=120,
                cwd=str(sub_dir),
            )
        except FileNotFoundError:
            # pytest not installed, use unittest
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(sub_dir), "-p", "test_*.py"],
                capture_output=True, text=True, timeout=120,
                cwd=str(sub_dir),
            )
        except subprocess.TimeoutExpired:
            return {
                "tests_found": True,
                "tests_passed": False,
                "tests_output": "Tests timed out after 120s",
                "tests_total": 0,
                "tests_failures": 0,
            }

        output = (proc.stdout + "\n" + proc.stderr).strip()
        # Truncate very long output
        if len(output) > 2000:
            output = output[:2000] + "\n... (truncated)"

        return {
            "tests_found": True,
            "tests_passed": proc.returncode == 0,
            "tests_output": output,
            "tests_total": len(test_files),
            "tests_failures": 0 if proc.returncode == 0 else 1,
        }

    def _try_launch(self, sub_dir: Path) -> dict:
        """Try to launch the app with a short timeout to catch startup crashes.

        Looks for main.py or app.py. Runs it for up to 5 seconds.
        If it survives 5s, it's probably fine (interactive app).
        If it exits with 0 before that, also fine (script).
        If it crashes immediately, that's a failure.
        """
        # Find entry point
        entry = None
        for candidate in ["main.py", "app.py", "run.py"]:
            if (sub_dir / candidate).exists():
                entry = sub_dir / candidate
                break

        if entry is None:
            # Look for any .py that has if __name__ == "__main__"
            for py_file in sub_dir.glob("*.py"):
                if py_file.name.startswith("test"):
                    continue
                try:
                    content = py_file.read_text(errors="ignore")
                    if '__name__' in content and '__main__' in content:
                        entry = py_file
                        break
                except OSError:
                    continue

        if entry is None:
            return {
                "launch_ok": None,
                "launch_output": "No entry point found (main.py, app.py, etc.)",
            }

        # Try running it with a short timeout
        # Use -c to import-check first (catches syntax errors and import crashes)
        entry_name = entry.name
        module_name = entry.stem
        try:
            import_proc = subprocess.run(
                [sys.executable, "-c", f"import {module_name}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(sub_dir),
            )
        except subprocess.TimeoutExpired:
            # Import took >10s — unusual but not necessarily a crash
            return {
                "launch_ok": None,
                "launch_output": f"Import of {entry_name} timed out (10s) — may be launching an interactive app at import time",
            }

        if import_proc.returncode != 0:
            output = (import_proc.stdout + "\n" + import_proc.stderr).strip()
            if len(output) > 1500:
                output = output[-1500:]
            return {
                "launch_ok": False,
                "launch_output": f"Import of {entry_name} failed:\n{output}",
            }

        # Import succeeded — try actually running it with a short timeout
        try:
            proc = subprocess.run(
                [sys.executable, entry_name],
                capture_output=True, text=True, timeout=5,
                cwd=str(sub_dir),
            )
            # If it exited within 5s, check return code
            if proc.returncode == 0:
                return {
                    "launch_ok": True,
                    "launch_output": f"{entry_name} ran and exited cleanly",
                }
            else:
                output = (proc.stdout + "\n" + proc.stderr).strip()
                if len(output) > 1500:
                    output = output[-1500:]
                return {
                    "launch_ok": False,
                    "launch_output": f"{entry_name} crashed (exit code {proc.returncode}):\n{output}",
                }
        except subprocess.TimeoutExpired:
            # App ran for 5s without crashing — it's an interactive app, that's fine
            return {
                "launch_ok": True,
                "launch_output": f"{entry_name} launched successfully (interactive app, ran 5s without crash)",
            }
