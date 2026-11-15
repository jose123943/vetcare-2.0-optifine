$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$vetcarePython = Join-Path $PSScriptRoot '.venv-wsgi\Scripts\python.exe'
if (!(Test-Path -LiteralPath $vetcarePython)) {
    python -m venv .venv-wsgi
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $vetcarePython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $vetcarePython scripts/configurar_wsgi.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $vetcarePython run.py check
exit $LASTEXITCODE
