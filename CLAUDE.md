# Agent Orchestrator

## Purpose
Multi-model agent orchestrator that launches parallel Claude Code sessions in split terminal panes. Each sub uses a different AI model, works in an isolated workspace. An orchestrator monitors progress and generates comparison reports.

## Tech Stack
- Python 3.12
- PyYAML (config), Rich (terminal UI)
- Claude Code CLI (subagent runtime)
- LiteLLM proxy (non-Claude model routing)
- Windows Terminal (`wt.exe`) on Windows, tmux on Linux/macOS

## Project Structure
```
src/
  cli.py          - Entry point (argparse): benchmark, status, report commands
  config.py       - Load config/config.yaml
  env.py          - Env configuration for subprocess launch (cmd.exe + bash)
  workspace.py    - Create run dirs + CLAUDE.md per sub, optional template copy
  launcher.py     - Launch split panes (WT on Windows, tmux on Linux/macOS)
  monitor.py      - Watch workspaces for progress.json + DONE.md
  metrics.py      - Collect file-based metrics from completed workspaces
  report.py       - Generate markdown comparison report
  validator.py    - Validate sub outputs (tests, launch check)
config/
  config.yaml     - Model registry + LiteLLM proxy config
workspaces/       - Runtime output, gitignored
run.cmd           - Windows launcher script
run.sh            - Linux/macOS launcher script
```

## Run Commands
```bash
# Benchmark
python -m src.cli benchmark --task "Build X" --models opus,sonnet,kimi-k2.5

# With a template folder (copied into each sub workspace)
python -m src.cli benchmark --task "Add auth" --models opus,sonnet --template ./starter-app

# Check status
python -m src.cli status

# Generate report
python -m src.cli report --run <run-name>
```

## Key Design Decisions
- Each sub is a full interactive Claude Code session (not --print)
- Cross-platform: Windows Terminal panes (Windows) / tmux panes+windows (Linux/macOS)
- tmux: 1-3 models use split panes, 4+ models use separate windows (tabs)
- tmux status bar always shows navigation shortcuts
- CLAUDE.md in each workspace gives the sub its task (auto-discovered by Claude Code)
- `--template` copies a local folder into each sub as `template/`, CLAUDE.md instructs agents to use it
- File-based progress tracking (progress.json, DONE.md)
- Extra env vars for all agents configurable via `env:` section in config.yaml
- Non-Claude models routed via ANTHROPIC_BASE_URL pointing to LiteLLM proxy
- On Linux, launcher creates a named tmux session and attaches to it
- Start scripts: `_start.cmd` (Windows) / `_start.sh` (Linux/macOS) per sub
