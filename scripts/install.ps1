# Creates the virtual environment and installs TradeMCP in editable mode.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv'

if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    Write-Host 'Creating virtual environment...'
    python -m venv $venv
}

$python = Join-Path $venv 'Scripts\python.exe'
Write-Host 'Installing TradeMCP...'
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -e $root --quiet
& $python -m pip install pytest --quiet

Write-Host ''
Write-Host 'TradeMCP installed.'
Write-Host ''
Write-Host 'Add this to your MCP client config:'
Write-Host ''
Write-Host @"
{
  "mcpServers": {
    "trademcp": {
      "command": "$python",
      "args": ["-m", "trademcp"]
    }
  }
}
"@
Write-Host ''
Write-Host 'Verify with:  .\.venv\Scripts\python.exe scripts\verify_all_tools.py'
