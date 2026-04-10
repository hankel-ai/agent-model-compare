"""CLI entry point for the agent orchestrator."""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console

from .config import get_litellm_config, is_claude_model, load_config
from .launcher import PaneLauncher, stop_subs
from .metrics import MetricsCollector
from .monitor import WorkspaceMonitor
from .report import save_report
from .validator import WorkspaceValidator
from .workspace import WorkspaceManager

console = Console()


def cmd_benchmark(args, config):
    """Launch a benchmark run across multiple models."""
    # Get task
    if args.task_file:
        task = Path(args.task_file).read_text()
    elif args.task:
        task = args.task
    else:
        console.print("[red]Error: provide --task or --task-file[/red]")
        sys.exit(1)

    models = [m.strip() for m in args.models.split(",")]
    if len(models) < 1:
        console.print("[red]Error: provide at least one model[/red]")
        sys.exit(1)

    # If any non-Claude models are requested, LiteLLM must be configured.
    non_claude = [m for m in models if not is_claude_model(m, config)]
    if non_claude and not get_litellm_config().get("url"):
        console.print(
            f"[red]Error:[/red] model(s) {non_claude} require a LiteLLM proxy.\n"
            "Set [cyan]LITELLM_BASE_URL[/cyan] (and [cyan]LITELLM_MASTER_KEY[/cyan] "
            "if your proxy requires auth) in [cyan].env[/cyan] — see [cyan].env.example[/cyan]."
        )
        sys.exit(1)

    # Resolve template path
    template = Path(args.template).resolve() if args.template else None

    # Create workspaces
    ws = WorkspaceManager()
    run_dir = ws.create_run(task=task, models=models, name=args.name, template=template)
    console.print(f"\n[bold]Created run:[/bold] {run_dir.name}")
    if template:
        console.print(f"[bold]Template:[/bold] {template}")
    for model in models:
        console.print(f"  {run_dir / f'sub-{model}'}")

    # Create Docker sandboxes if requested
    if args.sandbox:
        from .sandbox import create_sandbox, configure_sandbox_network, sandbox_name as sb_name

        litellm = get_litellm_config()
        litellm_url = litellm.get("url")
        sandbox_names = []

        console.print(f"\n[bold]Creating Docker sandboxes...[/bold]")
        created_names = []
        try:
            for model in models:
                name = sb_name(run_dir.name, model)
                sub_dir = run_dir / f"sub-{model}"
                console.print(f"  [cyan]{name}[/cyan]...")
                create_sandbox(name, sub_dir)
                created_names.append(name)

                if litellm_url and not is_claude_model(model, config):
                    configure_sandbox_network(name, litellm_url)

                sandbox_names.append(name)
        except RuntimeError as e:
            console.print(f"\n[red]Error: {e}[/red]")
            if created_names:
                from .sandbox import cleanup_sandboxes
                console.print("[yellow]Cleaning up partially created sandboxes...[/yellow]")
                cleanup_sandboxes(created_names)
            sys.exit(1)

        # Persist sandbox info in run config
        cfg_path = run_dir / "config.json"
        rc = json.loads(cfg_path.read_text())
        rc["sandbox"] = True
        rc["sandbox_names"] = sandbox_names
        cfg_path.write_text(json.dumps(rc, indent=2))

    # Launch panes
    console.print(f"\n[bold]Launching {len(models)} Claude Code sessions...[/bold]")
    launcher = PaneLauncher(config, sandbox=getattr(args, "sandbox", False))
    monitor_handled = launcher.launch_subs(run_dir, models)

    for model in models:
        route = "direct Anthropic API" if is_claude_model(model, config) else "via LiteLLM"
        console.print(f"  [cyan]{model}[/cyan] ({route})")

    if monitor_handled:
        # tmux: monitor runs in pane 0, user returns here after detaching
        console.print(f"\n[dim]Reattach: tmux attach -t {run_dir.name}[/dim]")
        return

    # Monitor (Windows — runs in the original terminal)
    console.print("")
    monitor = WorkspaceMonitor(run_dir, models)
    monitor.watch(interval=10)

    # If all done, generate report
    if monitor.all_done():
        _generate_report(run_dir, models)


def cmd_status(args, config):
    """Show status of a running or completed benchmark."""
    ws = WorkspaceManager()

    if args.run:
        run_dir = ws.find_run(args.run)
        if not run_dir:
            console.print(f"[red]Run not found: {args.run}[/red]")
            sys.exit(1)
    else:
        # Show most recent run
        runs = ws.list_runs()
        if not runs:
            console.print("[yellow]No runs found.[/yellow]")
            return
        run_dir = runs[0]

    run_config = ws.load_run_config(run_dir)
    models = run_config.get("models", [])

    if not models:
        console.print(f"[red]No model config found in {run_dir.name}[/red]")
        return

    monitor = WorkspaceMonitor(run_dir, models)

    if args.watch:
        monitor.watch(interval=5)
    else:
        # One-shot status display
        console.print(monitor._build_table())

        if monitor.all_done():
            console.print(f"\n[green]All subs completed.[/green]")
            console.print(f"Run [cyan]python -m src.cli report --run {run_dir.name}[/cyan] for the report.")


def cmd_stop(args, config):
    """Stop all Claude Code instances for a run."""
    ws = WorkspaceManager()

    if args.run:
        run_dir = ws.find_run(args.run)
        if not run_dir:
            console.print(f"[red]Run not found: {args.run}[/red]")
            sys.exit(1)
    else:
        runs = ws.list_runs()
        if not runs:
            console.print("[yellow]No runs found.[/yellow]")
            return
        run_dir = runs[0]

    console.print(f"[bold]Stopping subs for:[/bold] {run_dir.name}")
    killed = stop_subs(run_dir)

    if killed:
        console.print(f"[green]Stopped {killed} Claude Code instance(s).[/green]")
    else:
        console.print("[yellow]No running Claude Code instances found for this run.[/yellow]")

    # Clean up Docker sandboxes if this was a sandbox run
    run_config = ws.load_run_config(run_dir)
    sandbox_names = run_config.get("sandbox_names", [])
    if sandbox_names:
        from .sandbox import cleanup_sandboxes
        console.print(f"[bold]Removing Docker sandboxes...[/bold]")
        cleaned = cleanup_sandboxes(sandbox_names)
        console.print(f"[green]Removed {cleaned} sandbox(es).[/green]")


def cmd_report(args, config):
    """Generate comparison report for a completed run."""
    ws = WorkspaceManager()
    run_dir = ws.find_run(args.run)
    if not run_dir:
        console.print(f"[red]Run not found: {args.run}[/red]")
        sys.exit(1)

    run_config = ws.load_run_config(run_dir)
    models = run_config.get("models", [])
    _generate_report(run_dir, models)


def _generate_report(run_dir: Path, models: list[str]):
    """Collect metrics, validate workspaces, and generate the comparison report."""
    collector = MetricsCollector()
    metrics = [collector.collect(run_dir / f"sub-{m}", m) for m in models]

    # Validate: run tests and try launching each sub's app
    console.print("\n[bold]Validating sub outputs...[/bold]")
    validator = WorkspaceValidator()
    validations = []
    for m in models:
        console.print(f"  Validating [cyan]{m}[/cyan]...")
        v = validator.validate(run_dir / f"sub-{m}", m)
        validations.append(v)

        # Print inline results
        if v.get("tests_found"):
            if v["tests_passed"]:
                console.print(f"    Tests: [green]PASSED[/green]")
            else:
                console.print(f"    Tests: [red]FAILED[/red]")
        else:
            console.print(f"    Tests: [dim]none found[/dim]")

        launch = v.get("launch_ok")
        if launch is True:
            console.print(f"    Launch: [green]OK[/green]")
        elif launch is False:
            console.print(f"    Launch: [red]FAILED[/red]")
        else:
            console.print(f"    Launch: [dim]skipped[/dim]")

    # Merge validation results into metrics
    for m, v in zip(metrics, validations):
        m["tests_passed"] = v.get("tests_passed")
        m["tests_output"] = v.get("tests_output", "")
        m["launch_ok"] = v.get("launch_ok")
        m["launch_output"] = v.get("launch_output", "")

    report_path = save_report(run_dir, metrics)
    console.print(f"\n[bold green]Report saved:[/bold green] {report_path}")

    # Print the report
    console.print("")
    console.print(report_path.read_text())


def main():
    parser = argparse.ArgumentParser(
        description="Agent Orchestrator — benchmark AI models with identical tasks"
    )
    subparsers = parser.add_subparsers(dest="command")

    # benchmark
    bench = subparsers.add_parser("benchmark", help="Launch a benchmark run")
    bench.add_argument("--task", type=str, help="Task description")
    bench.add_argument("--task-file", type=str, help="Path to task description file")
    bench.add_argument("--models", type=str, required=True, help="Comma-separated model names")
    bench.add_argument("--name", type=str, help="Run name (optional)")
    bench.add_argument("--template", type=str, help="Path to a local folder to copy into each sub workspace as starter files")
    bench.add_argument("--sandbox", action="store_true", help="Run each model in a Docker sandbox")

    # status
    status = subparsers.add_parser("status", help="Check status of a run")
    status.add_argument("--run", type=str, help="Run name (partial match, default: latest)")
    status.add_argument("--watch", "-w", action="store_true", help="Continuously watch status")

    # stop
    stop = subparsers.add_parser("stop", help="Stop all Claude Code instances for a run")
    stop.add_argument("--run", type=str, help="Run name (partial match, default: latest)")

    # report
    report = subparsers.add_parser("report", help="Generate comparison report")
    report.add_argument("--run", type=str, required=True, help="Run name (partial match)")

    # list
    subparsers.add_parser("list", help="List all runs")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config()

    if args.command == "benchmark":
        cmd_benchmark(args, config)
    elif args.command == "status":
        cmd_status(args, config)
    elif args.command == "stop":
        cmd_stop(args, config)
    elif args.command == "report":
        cmd_report(args, config)
    elif args.command == "list":
        ws = WorkspaceManager()
        runs = ws.list_runs()
        if not runs:
            console.print("[yellow]No runs found.[/yellow]")
        else:
            for run_dir in runs:
                rc = ws.load_run_config(run_dir)
                models = ", ".join(rc.get("models", []))
                task_preview = rc.get("task", "")[:60]
                console.print(f"  [cyan]{run_dir.name}[/cyan]  models=[{models}]  task={task_preview}...")


if __name__ == "__main__":
    main()
