# Agent Orchestrator

Multi-model agent orchestrator that benchmarks AI models by giving them identical tasks in isolated workspaces. Each model runs as a full interactive Claude Code session in its own Windows Terminal pane.

## Quick Start

```bash
pip install pyyaml rich

python -m src.cli benchmark \
  --task "Build a Python CLI calculator with +,-,*,/ and unit tests" \
  --models opus,sonnet,kimi-k2.5
```

## Features

- Launch N Claude Code sessions in parallel Windows Terminal panes
- Each sub works in an isolated workspace directory
- Support Claude models (direct API) and any LiteLLM-supported model
- Real-time interaction: switch panes to monitor, answer questions, guide subs
- File-based progress tracking and completion detection
- Automated metrics collection and comparison reports

## Requirements

- Windows 11 with Windows Terminal
- Claude Code CLI
- Python 3.10+
- LiteLLM proxy (for non-Claude models)

## Usage

```bash
# Benchmark models on identical task
python -m src.cli benchmark --task "Build X" --models opus,sonnet,kimi-k2.5

# Check status of running benchmark
python -m src.cli status

# Generate comparison report
python -m src.cli report --run <run-name>
```

## Configuration

Edit `config/models.yaml` to configure Claude models and LiteLLM proxy settings.
