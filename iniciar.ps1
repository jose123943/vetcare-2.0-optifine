# Inicia la web local o el proceso de correo usando el entorno Python del proyecto.
param([switch]$Correo, [int]$Puerto = 8000)
# Ejecuta siempre desde el proyecto y evita generar cachés Python locales nuevas.
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location -LiteralPath $PSScriptRoot
$vetcarePython = Join-Path $PSScriptRoot '.venv-wsgi\Scripts\python.exe'
# Comprueba que exista el entorno aislado; no instala ni cambia dependencias al iniciar.
if (!(Test-Path -LiteralPath $vetcarePython)) {
    Write-Host 'Primero ejecuta: python -m venv .venv-wsgi'
    Write-Host 'Luego: .\.venv-wsgi\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}
# Selecciona el worker de correo o el servidor con comprobación previa de MySQL.
if ($Correo) {
    & $vetcarePython run.py worker
} else {
    & $vetcarePython run.py check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $vetcarePython run.py serve --port $Puerto
}
exit $LASTEXITCODE
