#!/usr/bin/env bash
# Creates the virtual environment and installs TradeMCP in editable mode.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv="$root/.venv"

if [ ! -x "$venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$venv"
fi

python="$venv/bin/python"
echo "Installing TradeMCP..."
"$python" -m pip install --upgrade pip --quiet
"$python" -m pip install -e "$root" --quiet
"$python" -m pip install pytest --quiet

echo ""
echo "TradeMCP installed."
echo ""
echo "Add this to your MCP client config:"
echo ""
cat <<EOF
{
  "mcpServers": {
    "trademcp": {
      "command": "$python",
      "args": ["-m", "trademcp"]
    }
  }
}
EOF
echo ""
echo "Verify with:  $python scripts/verify_all_tools.py"
