param([switch]$Correo, [int]$Puerto = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$vetcarePython = Join-Path $PSScriptRoot '.venv-wsgi\Scripts\python.exe'
if (!(Test-Path -LiteralPath $vetcarePython)) {
    Write-Host 'Primero ejecuta: python -m venv .venv-wsgi'
    Write-Host 'Luego: .\.venv-wsgi\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}
if ($Correo) {
    & $vetcarePython run.py worker
} else {
    & $vetcarePython run.py check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $vetcarePython run.py serve --port $Puerto
}
exit $LASTEXITCODE
