# Agent Orchestrator

Multi-model agent orchestrator that benchmarks AI models by giving them identical tasks in isolated workspaces. Each model runs as a full interactive Claude Code session in its own terminal pane (Windows Terminal on Windows, tmux on Linux/macOS).

## Quick Start

```bash
pip install pyyaml rich

# Windows
python -m src.cli benchmark \
  --task "Build a Python CLI calculator with +,-,*,/ and unit tests" \
  --models opus,sonnet,kimi-k2.5

# Linux/macOS
./run.sh --task "Build a Python CLI calculator" --models opus,sonnet
```

## Features

- Launch N Claude Code sessions in parallel split panes
- **Cross-platform**: Windows Terminal (`wt.exe`) on Windows, tmux on Linux/macOS
- Each sub works in an isolated workspace directory
- **Template folders**: provide starter files that get copied into every sub's workspace
- Support Claude models (direct API) and any LiteLLM-supported model
- Real-time interaction: switch panes to monitor, answer questions, guide subs
- File-based progress tracking and completion detection
- Automated metrics collection and comparison reports

## Requirements

- **Windows**: Windows 11 with Windows Terminal
- **Linux/macOS**: tmux (`sudo apt install tmux` / `brew install tmux`)
- Claude Code CLI
- Python 3.10+
- LiteLLM proxy (for non-Claude models)

## Usage

```bash
# Benchmark models on identical task
python -m src.cli benchmark --task "Build X" --models opus,sonnet,kimi-k2.5

# Provide a template folder with starter files for each sub
python -m src.cli benchmark --task "Add auth to this app" --models opus,sonnet \
  --template /path/to/starter-project

# Check status of running benchmark
python -m src.cli status

# Generate comparison report
python -m src.cli report --run <run-name>
```

### Template Folders

Use `--template` to specify a local directory whose contents are copied into a `template/` subdirectory in each sub's workspace. The generated CLAUDE.md instructs each agent to use these files as their starting point instead of building from scratch.

## Configuration

Edit `config/models.yaml` to configure Claude models and LiteLLM proxy settings.
