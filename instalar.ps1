# Prepara un entorno propio y conserva la configuración privada existente.
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location -LiteralPath $PSScriptRoot
$vetcarePython = Join-Path $PSScriptRoot '.venv-wsgi\Scripts\python.exe'
if (!(Test-Path -LiteralPath $vetcarePython)) {
    python -m venv .venv-wsgi
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
# Instala sólo dependencias declaradas y detiene el proceso ante cualquier error.
& $vetcarePython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# El asistente solicita secretos en privado; nunca se guardan dentro del código.
& $vetcarePython scripts/configurar_wsgi.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $vetcarePython run.py check
exit $LASTEXITCODE
