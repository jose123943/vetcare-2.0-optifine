# VetCare · Python WSGI + MySQL

Sistema veterinario con autenticación, clientes y múltiples mascotas, profesionales, citas, vacunas, tratamientos, facturas PDF, notificaciones y adopciones. Backend Python independiente, consultas SQL parametrizadas, frontend HTML/CSS/JavaScript y MySQL existente en Railway. No requiere Django, Flask, FastAPI ni un framework de frontend.

## Ejecutar en este equipo

La configuración privada `.env` y el entorno nuevo `.venv-wsgi` ya están preparados. En PowerShell, dentro de esta carpeta:

```powershell
.\.venv-wsgi\Scripts\python.exe run.py check
.\.venv-wsgi\Scripts\python.exe run.py serve
```

Abrir **http://127.0.0.1:8000**. Detener con Ctrl+C. También puede usarse `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1`. No es necesario activar el entorno ni ejecutar `manage.py`.

## Instalar en otro PC Windows

Se necesita Python 3.12 o superior, acceso de red a MySQL y las credenciales actuales. Descomprimir el código no instala Python ni transfiere los secretos privados.

```powershell
python -m venv .venv-wsgi
.\.venv-wsgi\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-wsgi\Scripts\python.exe scripts/configurar_wsgi.py
.\.venv-wsgi\Scripts\python.exe run.py check
.\.venv-wsgi\Scripts\python.exe run.py serve
```

El asistente solicita las credenciales una sola vez y escribe `.env`, sin mostrar la contraseña. Otra opción es `powershell -ExecutionPolicy Bypass -File .\instalar.ps1`. No copies el entorno virtual de otro PC: se debe recrear.

## Variables privadas

`MYSQLHOST`, `MYSQLPORT`, `MYSQLDATABASE`, `MYSQLUSER`, `MYSQLPASSWORD` y `VETCARE_SECRET_KEY` son obligatorias. La clave de firma debe tener al menos 32 caracteres. El asistente genera una nueva para instalaciones nuevas. La instalación migrada conserva la firma anterior para los resultados privados de adopciones. Las variables del proceso prevalecen sobre `.env`; usa una terminal nueva si quedaron credenciales antiguas en PowerShell.

En Windows, obtener **host y puerto públicos** desde MySQL → Connect en Railway. Obtener la contraseña vigente en Database → Config → Connection; no copiar asteriscos ni cambiar variables suponiendo que eso cambia la contraseña del servidor. Dentro de Railway se utiliza la referencia de red privada del mismo MySQL. Los valores pueden cambiar: `.env.example` no incluye credenciales ni valores inventados.

Si aparece 1045, corregir `MYSQLPASSWORD` y comprobar `MYSQLUSER` contra Connection. Si hay timeout/2003, comprobar `MYSQLHOST` y `MYSQLPORT` públicos y el estado del servicio. `run.py` oculta los detalles privados de las excepciones.

## Esquema, respaldo y cuentas

La base existente conserva todas sus tablas e identificadores. Para una instalación nueva o aplicar futuros cambios aditivos:

```powershell
.\.venv-wsgi\Scripts\python.exe run.py backup
.\.venv-wsgi\Scripts\python.exe run.py migrate
.\.venv-wsgi\Scripts\python.exe run.py check
```

Los SQL del directorio `sql` contienen sólo estructura; no borran ni recrean la base existente. El ejecutor registra sus checksums y evita aplicar cambios simultáneos. No modificar archivos SQL ya aplicados: crear otra migración aditiva.

Las cuentas previas siguen usando su usuario y contraseña; el primer acceso correcto convierte progresivamente su hash a Argon2. La sesión anterior debe iniciarse de nuevo. Para una base vacía, `python run.py create-admin` solicita una cuenta nueva mediante entrada protegida. No reinicia cuentas existentes ni proporciona contraseñas predeterminadas.

Las cuentas y los cuestionarios se administran en **Configuración**, dentro del dashboard. La gestión de cuentas requiere superadministrador.

## Correo

Completar `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL` y `DEFAULT_FROM_EMAIL` en `.env`. No activar TLS y SSL simultáneamente. En otra terminal:

```powershell
.\.venv-wsgi\Scripts\python.exe run.py worker
```

Registrar o modificar una cita guarda una notificación transaccional. El worker la envía fuera de la petición web. El dashboard muestra pendientes/fallidos y permite reintentar tras corregir SMTP. La generación MIME y el procesamiento están probados con transporte controlado; la entrega a un buzón externo requiere configurar y verificar el proveedor real.

## Pruebas y documentación

```powershell
.\.venv-wsgi\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv-wsgi\Scripts\python.exe scripts/probar_wsgi.py
```

Las pruebas crean una base **nueva y aislada** con prefijo `test_vetcare_`; no escriben fixtures en `railway`. Se requiere permiso MySQL CREATE DATABASE. Las bases de prueba se conservan para inspección y nunca se confunden con la base operativa.

Para repetir los recorridos de navegador, después de la suite ejecutar `python scripts/preparar_wsgi_navegador.py` y, en otra terminal, `python scripts/servidor_pruebas_wsgi.py`, usando siempre el Python de `.venv-wsgi`. Instalar Node.js y Playwright Core fuera del proyecto:

```powershell
npm install --prefix "$env:TEMP\vetcare_browser" playwright-core
$env:VETCARE_PLAYWRIGHT_MODULE = "$env:TEMP\vetcare_browser\node_modules\playwright-core"
node scripts/prueba_navegador.cjs
.\.venv-wsgi\Scripts\python.exe scripts/preparar_wsgi_navegador.py
node scripts/prueba_adopciones.cjs
node scripts/prueba_configuracion.cjs
node scripts/prueba_crud.cjs
```

Estos scripts usan Edge instalado en Windows y el puerto 8001, con usuarios y datos sintéticos. El preparador renueva la cookie revocada por la prueba de logout; no escribe cookies privadas en el repositorio.

- [Arquitectura, inventario funcional y sustentación](docs/MIGRACION_WSGI.md).
- [Despliegue en Railway](docs/RAILWAY.md).
- [Resultados y comprobaciones pendientes](docs/PRUEBAS_WSGI.md).
- `docs/endpoints_wsgi.json`: métodos, rutas, permisos e idempotencia.
- `docs/wsgi_integridad_completa.json`: comparación de las 33 tablas originales sin datos privados.
- `docs/wsgi_rendimiento_*.json`: muestras comparativas de rendimiento.

La versión anterior permanece recuperable mediante el respaldo privado completo creado antes de migrar. No se incluyen `.env`, fotos privadas, entornos virtuales ni respaldos de datos en el ZIP compartido.
