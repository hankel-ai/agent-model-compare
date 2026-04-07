# Agent Orchestrator

Multi-model agent orchestrator that benchmarks AI models by giving them identical tasks in isolated workspaces. Each model runs as a full interactive Claude Code session in its own terminal pane (Windows Terminal on Windows, tmux on Linux/macOS).

## Quick Start

```bash
pip install pyyaml rich

# (Optional) configure LiteLLM proxy and other env vars
cp .env.example .env
# edit .env — see "Configuration" below for what each var does

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

`config/config.yaml` declares which model names are routed directly to the
Anthropic API (`claude_models`). Anything not in that list is routed via
LiteLLM.

Everything else lives in `.env` (gitignored). Copy `.env.example` to `.env`
and set whichever variables you need — all are optional. If a variable is
unset or empty, the related feature is disabled.

| Variable | Purpose |
|---|---|
| `LITELLM_BASE_URL` | Base URL of your LiteLLM proxy (e.g. `http://localhost:4000`). Required to use any non-Claude model. |
| `LITELLM_MASTER_KEY` | Auth token for your LiteLLM proxy. |
| `HTTPS_PROXY` | Outbound proxy injected into every agent subprocess. |
| `NODE_EXTRA_CA_CERTS` | Extra CA bundle for Node-based tools (e.g. Claude Code CLI). Path can be absolute or relative to the project root. |
| `NVIDIA_NIM_API_KEY` | Used by `list_models.py` only. |
