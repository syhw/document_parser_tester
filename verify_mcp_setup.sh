#!/bin/bash
# MCP Setup Verification Script

echo "======================================================================"
echo "  MCP SETUP VERIFICATION"
echo "======================================================================"
echo ""

# 1. Check config file exists
echo "1. Checking MCP configuration file..."
if [ -f ~/.config/claude-code/mcp_servers.json ]; then
    echo "   ✅ Config file exists: ~/.config/claude-code/mcp_servers.json"
    echo ""
    echo "   Contents:"
    cat ~/.config/claude-code/mcp_servers.json | head -20
    echo ""
else
    echo "   ❌ Config file not found!"
    exit 1
fi

# 2. Check npx is available
echo "2. Checking npx availability..."
if command -v npx &> /dev/null; then
    NPX_VERSION=$(npx --version)
    echo "   ✅ npx is installed: version $NPX_VERSION"
    echo "   ✅ Location: $(which npx)"
else
    echo "   ❌ npx not found! Please install Node.js"
    exit 1
fi

# 3. Check if Z.AI MCP server package exists
echo ""
echo "3. Testing Z.AI MCP server package..."
echo "   Checking if @z_ai/mcp-server is available..."
npx -y @z_ai/mcp-server --help 2>&1 | head -10 || echo "   ⚠️  Package fetch may take a moment on first run"

echo ""
echo "======================================================================"
echo "  SETUP COMPLETE ✅"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. EXIT this Claude Code session completely"
echo "  2. Start a NEW Claude Code session"
echo "  3. In the new session, ask: 'Do you have access to MCP tools?'"
echo "  4. You should see: mcp__zai_mcp_server__image_analysis"
echo ""
echo "Then you can run:"
echo "  claude -p test_mcp_zai_GLM.py my_tests/2510.02387.pdf"
echo ""
echo "======================================================================"
