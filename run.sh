#!/usr/bin/env bash
set -e

# Check for tmux
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is required on Linux/macOS. Install it with:"
    echo "  Ubuntu/Debian: sudo apt install tmux"
    echo "  macOS: brew install tmux"
    exit 1
fi

# Check for claude CLI
if ! command -v claude &> /dev/null; then
    echo "Error: claude CLI not found in PATH."
    exit 1
fi

if [ $# -eq 0 ]; then
    echo ""
    echo "Usage: ./run.sh --task \"prompt\" --models model1,model2 [--template /path/to/folder]"
    exit 1
fi

python3 -m src.cli benchmark "$@"
