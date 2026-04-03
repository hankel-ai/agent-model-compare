# Agent Orchestrator

## Purpose
Multi-model agent orchestrator that launches parallel Claude Code sessions in Windows Terminal panes. Each sub uses a different AI model, works in an isolated workspace. An orchestrator monitors progress and generates comparison reports.

## Tech Stack
- Python 3.12
- PyYAML (config), Rich (terminal UI)
- Claude Code CLI (subagent runtime)
- LiteLLM proxy (non-Claude model routing)
- Windows Terminal (`wt.exe`) for pane management

## Project Structure
```
src/
  cli.py          - Entry point (argparse): benchmark, status, report commands
  config.py       - Load config/models.yaml
  env.py          - Env sanitization for subprocess launch
  workspace.py    - Create run dirs + CLAUDE.md per sub
  launcher.py     - Launch WT split panes with claude sessions
  monitor.py      - Watch workspaces for progress.json + DONE.md
  metrics.py      - Collect file-based metrics from completed workspaces
  report.py       - Generate markdown comparison report
config/
  models.yaml     - Model registry + LiteLLM proxy config
workspaces/       - Runtime output, gitignored
```

## Run Commands
```bash
# Benchmark
python -m src.cli benchmark --task "Build X" --models opus,sonnet,kimi-k2.5

# Check status
python -m src.cli status

# Generate report
python -m src.cli report --run <run-name>
```

## Key Design Decisions
- Each sub is a full interactive Claude Code session (not --print)
- Windows Terminal panes for real-time interaction
- CLAUDE.md in each workspace gives the sub its task (auto-discovered by Claude Code)
- File-based progress tracking (progress.json, DONE.md)
- Must clear CLAUDE_CODE_USE_VERTEX + ANTHROPIC_VERTEX_PROJECT_ID from subprocess env
- Non-Claude models routed via ANTHROPIC_BASE_URL pointing to LiteLLM proxy
