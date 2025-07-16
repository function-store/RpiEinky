#!/bin/bash
# Foolproof virtual environment activation script
# This script detects if you forgot to use 'source' and helps you fix it!

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to virtual environment (relative to script location)
VENV_PATH="$SCRIPT_DIR/../eink_env"

# Check if script is being sourced (correct way) or executed directly (wrong way)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Script is being executed directly - this won't work!
    echo "⚠️  WHOOPS! You need to SOURCE this script, not execute it directly."
    echo ""
    echo "❌ What you did:     ./activate_env.sh"
    echo "✅ What you need:    source activate_env.sh"
    echo ""
    echo "💡 Here's the correct command to copy/paste:"
    echo "   source $(basename "$0")"
    echo ""
    echo "🤔 Why? Virtual environment activation needs to modify your current"
    echo "   shell, not create a new subprocess that immediately disappears."
    echo ""
    echo "📋 Pro tip: You can also use the shorthand: . $(basename "$0")"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at: $VENV_PATH"
    echo "Please create it first with: python3 -m venv ../eink_env"
    return 1
fi

# Check if activate script exists
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "❌ Activate script not found at: $VENV_PATH/bin/activate"
    echo "Virtual environment may be corrupted. Try recreating it."
    return 1
fi

# Activate the virtual environment
echo "🚀 Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Verify activation
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
    echo "📍 Current directory: $(pwd)"
    echo "🐍 Python: $(which python)"
    echo ""
    echo "To deactivate, run: deactivate"
else
    echo "❌ Failed to activate virtual environment"
    return 1
fi 