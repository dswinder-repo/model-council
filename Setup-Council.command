#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Model Council — One-Click Setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
#  Double-click this file to run it.
#  It will:
#   1. Install Python dependencies
#   2. Register the MCP server with Claude Code
#   3. Done — Model Council will be available in all future sessions
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

# Auto-detect where this script lives (= where server.py is)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_PATH="$SCRIPT_DIR/server.py"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Model Council — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verify server.py exists
if [ ! -f "$SERVER_PATH" ]; then
    echo "❌ Can't find server.py at: $SERVER_PATH"
    echo "   Make sure this script is in the same folder as server.py"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo "✓ Found server at: $SERVER_PATH"
echo ""

# Step 1: Install Python dependencies
echo "Step 1: Installing Python dependencies..."
pip3 install "mcp[cli]>=1.0.0" "httpx[socks]>=0.27.0" "pydantic>=2.0.0" --quiet 2>&1
echo "✓ Dependencies installed"
echo ""

# Step 2: Verify server loads
echo "Step 2: Verifying server..."
cd "$SCRIPT_DIR"
python3 -c "import server; print('✓ Server module verified')"
echo ""

# Step 3: Get API key
echo "Step 3: OpenRouter API Key"
echo ""
echo "  Paste your OpenRouter API key below."
echo "  (Get one at https://openrouter.ai/settings/keys)"
echo ""
read -p "  API Key: " API_KEY

if [ -z "$API_KEY" ]; then
    echo ""
    echo "❌ No API key provided. You can re-run this script later."
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo ""

# Step 4: Check if Claude Code CLI exists
if ! command -v claude &> /dev/null; then
    echo "⚠️  Claude Code CLI not found in PATH."
    echo ""
    echo "  Two options:"
    echo ""
    echo "  Option A — If you have Claude Code installed, try:"
    echo "    export PATH=\"\$PATH:/usr/local/bin\""
    echo "    Then re-run this script."
    echo ""
    echo "  Option B — Manual setup: Add this to Claude Desktop → Settings → Developer → MCP Servers:"
    echo "    Name:    model-council"
    echo "    Command: python3"
    echo "    Args:    $SERVER_PATH"
    echo "    Env:     OPENROUTER_API_KEY=$API_KEY"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo "✓ Found Claude Code CLI"
echo ""

# Step 5: Remove old config if exists (in case of re-run)
echo "Step 4: Registering MCP server..."
claude mcp remove model-council -s user 2>/dev/null || true

# Register with Claude Code (user scope = available everywhere)
claude mcp add model-council \
    -s user \
    -e OPENROUTER_API_KEY="$API_KEY" \
    -- python3 "$SERVER_PATH"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Model Council is now registered globally."
echo "  It will be available in all Claude Code and Cowork sessions."
echo ""
echo "  Try it:"
echo "    • In Cowork: 'Council this: [your research question]'"
echo "    • In Claude Code: Ask to use council_research tool"
echo ""
echo "  Default models: Claude Sonnet 4, GPT-4.1, Gemini 2.5 Pro"
echo ""
read -p "Press Enter to close..."
