"""Generate markdown comparison report from collected metrics."""

import json
from datetime import datetime
from pathlib import Path


def generate_report(run_dir: Path, metrics: list[dict]) -> str:
    """Generate a markdown comparison report.

    Args:
        run_dir: The run directory path.
        metrics: List of per-model metrics dicts from MetricsCollector.

    Returns:
        Markdown string.
    """
    config_path = run_dir / "config.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {}

    task = config.get("task", "Unknown task")
    models = [m["model"] for m in metrics]
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append(f"# Benchmark Report")
    lines.append(f"")
    lines.append(f"**Run:** {run_dir.name}  ")
    lines.append(f"**Date:** {date}  ")
    lines.append(f"**Models:** {', '.join(models)}")
    lines.append(f"")
    lines.append(f"## Task")
    lines.append(f"")
    lines.append(task)
    lines.append(f"")

    # Comparison table
    lines.append(f"## Comparison")
    lines.append(f"")

    # Header
    header = "| Metric | " + " | ".join(models) + " |"
    separator = "|--------|" + "|".join(["-------" for _ in models]) + "|"
    lines.append(header)
    lines.append(separator)

    # Rows
    def row(label, key, fmt=str):
        values = [fmt(m.get(key, "")) for m in metrics]
        return f"| {label} | " + " | ".join(values) + " |"

    lines.append(row("Files Created", "files_created"))
    lines.append(row("Code Files", "code_files"))
    lines.append(row("Lines of Code", "lines_of_code"))
    lines.append(row("Test Files", "test_files"))
    lines.append(row("Test Lines", "test_lines"))
    lines.append(row("Has Tests", "has_tests", lambda v: "yes" if v else "no"))

    # Validation rows (only if validation was run)
    if any(m.get("tests_passed") is not None or m.get("launch_ok") is not None for m in metrics):
        def fmt_tests(v):
            if v is None:
                return "-"
            return "PASS" if v else "**FAIL**"

        def fmt_launch(v):
            if v is None:
                return "-"
            return "OK" if v else "**CRASH**"

        lines.append(row("Tests Pass", "tests_passed", fmt_tests))
        lines.append(row("App Launches", "launch_ok", fmt_launch))

    lines.append(f"")

    # Per-model summaries
    lines.append(f"## Sub Summaries")
    lines.append(f"")

    for m in metrics:
        lines.append(f"### {m['model']}")
        lines.append(f"")

        # Validation results
        if m.get("tests_passed") is not None or m.get("launch_ok") is not None:
            lines.append("#### Validation")
            lines.append("")
            if m.get("tests_passed") is not None:
                status = "PASSED" if m["tests_passed"] else "FAILED"
                lines.append(f"**Tests:** {status}")
                lines.append(f"```")
                lines.append(m.get("tests_output", "").strip())
                lines.append(f"```")
                lines.append("")
            if m.get("launch_ok") is not None:
                status = "OK" if m["launch_ok"] else "FAILED"
                lines.append(f"**App Launch:** {status}")
                launch_out = m.get("launch_output", "").strip()
                if launch_out:
                    lines.append(f"```")
                    lines.append(launch_out)
                    lines.append(f"```")
                lines.append("")

        summary = m.get("done_summary")
        if summary:
            lines.append("#### Summary")
            lines.append("")
            lines.append(summary)
        else:
            lines.append("*No DONE.md found — sub may not have completed.*")
        lines.append(f"")

    return "\n".join(lines)


def save_report(run_dir: Path, metrics: list[dict]) -> Path:
    """Generate and save the report to the run directory."""
    report = generate_report(run_dir, metrics)
    report_path = run_dir / "report.md"
    report_path.write_text(report)

    # Also save raw metrics as JSON
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))

    return report_path
