#!/bin/bash
# Model Council — Setup Script
# Run this from your Mac terminal to install dependencies
# Usage: cd /path/to/Claude/labs/model-council && bash setup.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Model Council — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install via: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "✓ Found $PYTHON_VERSION"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install "mcp[cli]>=1.0.0" "httpx[socks]>=0.27.0" "pydantic>=2.0.0" --quiet

echo "✓ Dependencies installed"

# Test import
echo ""
echo "Testing server module..."
python3 -c "import server; print('✓ Server module loads cleanly')"

# Prompt for API key
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To use Model Council, add it to your Cowork MCP config."
echo ""
echo "Option 1 — Claude Desktop / Cowork:"
echo "  Open Claude Desktop → Settings → Developer → MCP Servers → Add"
echo "  Name: model-council"
echo "  Command: python3"
echo "  Args: $(pwd)/server.py"
echo "  Env: OPENROUTER_API_KEY=<your-key>"
echo ""
echo "Option 2 — Quick CLI test:"
echo "  OPENROUTER_API_KEY=<your-key> python3 server.py --cli 'Your research question'"
echo ""
echo "Option 3 — Claude Code (if using):"
echo "  claude mcp add model-council -- python3 $(pwd)/server.py"
echo "  Then set env: OPENROUTER_API_KEY=<your-key>"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
