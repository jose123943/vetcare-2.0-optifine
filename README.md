# VetCare · Python WSGI + MySQL

[Mapa de carpetas y bloques de código](docs/ESTRUCTURA.md) · [Publicación en Railway](docs/RAILWAY.md)

El frontend está separado en `frontend/assets/css`, `js` e `images`; las pruebas de navegador están en `tests/browser` y los informes en `docs/evidencias`. Los bloques Python, JavaScript, CSS y HTML incluyen explicaciones sobre su responsabilidad.

## Preparar el paquete web

```powershell
.\.venv-wsgi\Scripts\python.exe scripts/verificar_despliegue.py --con-base
.\.venv-wsgi\Scripts\python.exe scripts/build_assets.py
.\.venv-wsgi\Scripts\python.exe scripts/empaquetar_wsgi.py
```

`dist/VetCare-web.zip` contiene el código necesario para publicar, sin credenciales, entornos ni evidencias pesadas. El paquete `VetCare-WSGI-railway.zip` conserva también los informes y capturas. Docker construye únicamente los directorios de ejecución y prepara gzip para CSS/JS; no requiere Node ni conexión SQL durante el build.

La configuración de Railway está preparada en los archivos raíz. El despliegue público requiere configurar las referencias MySQL, la firma privada, el dominio y el volumen, según [la guía](docs/RAILWAY.md). Gmail por SMTP necesita un plan que habilite SMTP en Railway; la guía enlaza la restricción oficial.

Sistema veterinario con autenticación, clientes y múltiples mascotas, profesionales, citas, vacunas, tratamientos, facturas PDF, notificaciones y adopciones. Backend Python independiente, consultas SQL parametrizadas, frontend HTML/CSS/JavaScript y MySQL existente en Railway. No requiere Django, Flask, FastAPI ni un framework de frontend.

[Guía completa de funciones y pestañas](vetcare-funciones.md). La sesión autenticada se mantiene durante la ejecución del programa, hasta cerrar sesión o reiniciar el servidor; ya no tiene el límite automático de ocho horas. Las sesiones de visitantes del catálogo conservan su caducidad independiente.

Los buscadores de Clientes y mascotas y Agendar cita despliegan propietarios sin exigir texto previo y permiten seguir buscando normalmente. Las citas nuevas sólo se crean como **Programada**; al terminar su duración pasan a **Atendida**. El monitor del servidor revisa cada 15 segundos con hora de Colombia, sin depender del worker de correo. La agenda abierta también actualiza los estados automáticamente.

Las facturas utilizan un selector de **Transferencia**, **Efectivo** o **Tarjeta**. [Detalle de la limpieza y reglas actuales](docs/LIMPIEZA_PROYECTO.md).

La última limpieza deja la base operativa vacía, conservando todos los superusuarios y el cuestionario. Para previsualizar otra limpieza: `python scripts/limpiar_datos.py`. Sólo `--aplicar` respalda y vacía datos; nunca se ejecuta al iniciar.

Para previsualizar la carga ficticia: `python scripts/preparar_demostracion.py`. La opción explícita `--aplicar` respalda y reemplaza datos operativos, conserva superusuarios/configuración y carga cinco clientes con nueve mascotas, cinco veterinarios, citas, facturas, vacunas, tratamientos y mascotas/solicitudes de adopción. Nunca se ejecuta automáticamente al iniciar la aplicación. Los correos de demostración no se envían.

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

Los superusuarios conservados siguen usando su usuario y contraseña; la limpieza de demostración solicitada elimina las demás cuentas. El primer acceso correcto convierte progresivamente los hashes heredados a Argon2. La sesión anterior debe iniciarse de nuevo. Para una base vacía, `python run.py create-admin` solicita una cuenta nueva mediante entrada protegida. No reinicia cuentas existentes ni proporciona contraseñas predeterminadas.

Las cuentas y los cuestionarios se administran en **Configuración**, dentro del dashboard. La gestión de cuentas requiere superadministrador.

## Correo

Para **Gmail**, activa la verificación en dos pasos y crea una contraseña de aplicación para VetCare en [tu cuenta de Google](https://myaccount.google.com/apppasswords). Introduce esos datos exclusivamente en la terminal local:

```powershell
.\.venv-wsgi\Scripts\python.exe scripts/configurar_gmail.py
```

El asistente solicita la dirección remitente y la contraseña de aplicación de 16 caracteres mediante entrada oculta, comprueba TLS y autenticación **sin enviar correos**, y guarda únicamente las variables de correo en `.env`. Conserva las credenciales MySQL y la clave de firma. Si la comprobación falla, no guarda los nuevos datos.

Gmail utiliza `smtp.gmail.com:587`, `EMAIL_USE_TLS=true` y `EMAIL_USE_SSL=false`; el remitente corresponde a la misma cuenta que autentica. La configuración puede comprobarse de nuevo con `python scripts/configurar_gmail.py --comprobar`, usando el Python de `.venv-wsgi`. [Servidor y puerto SMTP oficiales](https://developers.google.com/workspace/gmail/imap/imap-smtp).

Google exige verificación en dos pasos para generar contraseñas de aplicación. Algunas cuentas de organizaciones o con Protección Avanzada no ofrecen esta opción; si no aparece, consultar las restricciones de la cuenta y la [ayuda oficial de Google](https://support.google.com/accounts/answer/185833?hl=es). La aplicación usa SMTP y no requiere compartir credenciales en el chat.

Completar `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL` y `DEFAULT_FROM_EMAIL` en `.env`. No activar TLS y SSL simultáneamente. En otra terminal:

```powershell
.\.venv-wsgi\Scripts\python.exe run.py worker
```

Registrar o modificar una cita guarda una notificación transaccional. El worker la envía fuera de la petición web. El dashboard muestra pendientes/fallidos y permite reintentar tras corregir SMTP. La generación MIME y el procesamiento están probados con transporte controlado; la entrega a un buzón externo requiere configurar y verificar el proveedor real.

### Correo en Google Cloud Run

La interfaz activa ahora una **petición HTTP separada de envío** después de guardar o editar una cita y después de reintentar un mensaje. La cita queda confirmada antes de contactar con Gmail. En **Notificaciones** aparece **Procesar pendientes**, se procesa la cola al abrir la pestaña y se actualizan los estados cada 15 segundos mientras está visible. No necesitas mantener un worker en tu PC para este modo.

Esta petición termina después del intento SMTP: no depende de un hilo que Cloud Run pueda suspender al finalizar la respuesta. [CPU y trabajo en segundo plano en Cloud Run](https://docs.cloud.google.com/run/docs/tips/general). Se reclama un mensaje por petición; el navegador continúa en lotes de hasta cinco y la pestaña de notificaciones sigue con los restantes. El worker independiente sigue siendo compatible y ambos consumidores usan la misma reclamación SQL para no enviar el mismo registro simultáneamente.

El `.env` de tu equipo **no se despliega**. En Google Cloud Console → Cloud Run → tu servicio → **Editar y desplegar una revisión nueva** → **Variables y secretos**, configura:

| Variable | Valor que debe tener en el servicio web |
|---|---|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `true` |
| `EMAIL_USE_SSL` | `false` |
| `EMAIL_HOST_USER` | Tu dirección completa de Gmail |
| `EMAIL_HOST_PASSWORD` | Su contraseña de aplicación vigente de 16 caracteres, preferiblemente desde Secret Manager |
| `DEFAULT_FROM_EMAIL` | La misma dirección que `EMAIL_HOST_USER` |

Despliega la revisión con esos valores y el código actualizado. Abre **Notificaciones**: si faltan variables, la página indica sus nombres sin mostrar valores privados. **Configuración presente** sólo acredita validación local del formato; cada mensaje pasa a **Enviada** únicamente después de aceptación SMTP. **Pendiente, 0 intentos** significa que todavía no hay un intento registrado, no que Gmail haya aceptado el envío.

Si cierras el navegador antes de activar el envío, la notificación sigue en MySQL y puede procesarse al abrir Notificaciones. Para consumir la cola permanentemente sin clientes conectados, configura un consumidor de nube independiente o tareas programadas autenticadas; este modo HTTP no acredita un servicio de tareas autónomo. Los datos `.invalid` siguen en **Demostración** y no se envían. Los entornos de pruebas rechazan el transporte real salvo cuando la prueba inyecta un receptor controlado.

Después de configurar Gmail, detén el worker anterior con Ctrl+C y vuelve a iniciarlo para que lea el `.env` actualizado. En Notificaciones pulsa **Reintentar** en los mensajes fallidos y luego **Actualizar**. El worker nuevo comprueba la configuración antes de tomar mensajes de la cola; los errores de configuración y autenticación se muestran sin revelar respuestas privadas del proveedor. `Enviada` indica aceptación por el servidor SMTP, no confirmación de lectura o de ubicación en la bandeja de entrada.

## Pruebas y documentación

```powershell
.\.venv-wsgi\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv-wsgi\Scripts\python.exe scripts/probar_wsgi.py
```

Las pruebas crean una base **nueva y aislada** con prefijo `test_vetcare_`; no escriben fixtures en `railway`. Se requiere permiso MySQL CREATE DATABASE. Las bases de prueba se conservan para inspección y nunca se confunden con la base operativa.

Para repetir los recorridos de navegador, después de la suite ejecutar `python tests/browser/preparar_wsgi_navegador.py` y, en otra terminal, `python tests/browser/servidor_pruebas_wsgi.py`, usando siempre el Python de `.venv-wsgi`. Instalar Node.js y Playwright Core fuera del proyecto:

```powershell
npm install --prefix "$env:TEMP\vetcare_browser" playwright-core
$env:VETCARE_PLAYWRIGHT_MODULE = "$env:TEMP\vetcare_browser\node_modules\playwright-core"
node tests/browser/prueba_navegador.cjs
.\.venv-wsgi\Scripts\python.exe tests/browser/preparar_wsgi_navegador.py --reset-demo
node tests/browser/prueba_adopciones.cjs
node tests/browser/prueba_configuracion.cjs
node tests/browser/prueba_crud.cjs
.\.venv-wsgi\Scripts\python.exe tests/browser/preparar_wsgi_navegador.py --reset-demo
node tests/browser/prueba_demo_sesion_encuesta.cjs
.\.venv-wsgi\Scripts\python.exe tests/browser/preparar_wsgi_navegador.py --reset-demo
Copy-Item "$env:TEMP\vetcare_wsgi_test_database.json" "$env:TEMP\vetcare_browser_active_database.json"
node tests/browser/prueba_agenda_propietarios.cjs
```

Estos scripts usan Edge instalado en Windows y el puerto 8001, con usuarios y datos sintéticos. El preparador renueva la cookie revocada por la prueba de logout; no escribe cookies privadas en el repositorio.

- [Arquitectura, inventario funcional y sustentación](docs/MIGRACION_WSGI.md).
- [Despliegue en Railway](docs/RAILWAY.md).
- [Resultados y comprobaciones pendientes](docs/PRUEBAS_WSGI.md).
- `docs/evidencias/endpoints_wsgi.json`: métodos, rutas, permisos e idempotencia.
- `docs/evidencias/wsgi_integridad_completa.json`: comparación de las 33 tablas originales sin datos privados.
- `docs/evidencias/wsgi_rendimiento_*.json`: muestras comparativas de rendimiento.

La versión anterior permanece recuperable mediante el respaldo privado completo creado antes de migrar. No se incluyen `.env`, fotos privadas, entornos virtuales ni respaldos de datos en el ZIP compartido.
