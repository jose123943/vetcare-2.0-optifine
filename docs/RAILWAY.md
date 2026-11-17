# VetCare WSGI en Railway

## Estado

La aplicación se comprobó en Windows y en Linux (WSL, Python 3.14.4) con Gunicorn, dos workers, MySQL en una base aislada, HTTPS simulado por proxy, rutas protegidas y recursos gzip con revalidación ETag/304. La suite y los resultados están en `evidencias/`. No se ha publicado ni sustituido un servicio web público.

El Dockerfile usa Python 3.12 y la configuración de CI comprueba Python 3.12/3.14 y construcción de imagen. El motor Docker de este equipo está detenido: la imagen final aún debe construirse, y dominio, volumen y correo deben verificarse en Railway. El arranque Linux comprobado no se presenta como una construcción Docker ni como publicación HTTPS externa.

## Paquetes y comprobación previa

```powershell
.\.venv-wsgi\Scripts\python.exe scripts/verificar_despliegue.py --con-base
.\.venv-wsgi\Scripts\python.exe scripts/build_assets.py
.\.venv-wsgi\Scripts\python.exe scripts/empaquetar_wsgi.py
```

La revisión SQL es de sólo lectura. `dist/VetCare-web.zip` omite evidencias históricas pesadas; el ZIP completo conserva informes y capturas. Ambos excluyen `.env`, fotos, entornos virtuales y respaldos. No se necesita Node para ejecutar ni construir la aplicación.

Con Docker activo, `docker build -t vetcare-web .` comprueba la imagen. Docker copia sólo código, recursos, SQL y scripts de ejecución, reutiliza la capa de dependencias y genera los recursos comprimidos sin conectar MySQL. Las variables privadas se suministran al ejecutar o desde Railway, nunca durante el build. [Dockerfiles en Railway](https://docs.railway.com/builds/dockerfiles).

## Servicio web

1. Guardar una copia privada reciente con `python run.py backup` y conservar la versión anterior para rollback. Usar el paquete de código revisado sin `.env`, datos, fotos ni entornos virtuales.
2. Crear el servicio web desde el código autorizado. `railway.json` selecciona Dockerfile. La imagen instala dependencias y copia HTML/assets; no conecta MySQL durante la construcción y no necesita un compilador MySQL nativo.
3. Configurar referencias al **MySQL existente** para `MYSQLHOST`, `MYSQLPORT`, `MYSQLDATABASE`, `MYSQLUSER`, `MYSQLPASSWORD`. Usar su red privada, disponible entre servicios del mismo proyecto y entorno. [Red privada de Railway](https://docs.railway.com/networking/private-networking).
4. Configurar `VETCARE_PRODUCTION=true`, `VETCARE_SERVICE=web`, `VETCARE_SECRET_KEY` y `MEDIA_ROOT=/data/media`. Conservar la clave de firma anterior si se necesita mantener el acceso de visitantes a solicitudes antiguas; no publicarla.
5. Montar almacenamiento persistente en `/data` y copiar las fotos previas a `/data/media` preservando sus nombres relativos. Los volúmenes persisten datos entre despliegues; no usar sólo el disco efímero de la imagen. [Volúmenes](https://docs.railway.com/volumes).
6. Generar el dominio público. La aplicación admite `RAILWAY_PUBLIC_DOMAIN`; para dominios propios añadirlos a `VETCARE_ALLOWED_HOSTS` separados por comas. No incluir esquema ni puerto en esa lista.
7. Predeploy ejecuta `python run.py migrate`; sólo añade estructura y siembra el cuestionario únicamente si no existe ninguno. Los comandos predeploy no acceden al volumen; las imágenes se guardan durante la ejecución web. [Predeploy](https://docs.railway.com/deployments/pre-deploy-command).
8. Gunicorn inicia `vetcare.wsgi:application` usando `$PORT` mediante `gunicorn.conf.py`. `/health/live/` valida el proceso; `/health/ready/` comprueba MySQL sin devolver credenciales.

`DB_POOL_SIZE` admite entre 1 y 32 conexiones por proceso. El valor inicial 8 cubre los cuatro threads web y el monitor de agenda. `WEB_CONCURRENCY=2` configura dos procesos; ajustar ambos parámetros al tamaño del servicio. Los workers se reciclan con margen aleatorio para controlar memoria sin invalidar sesiones del mismo despliegue. `MEDIA_ROOT` debe ser absoluto; el predeploy no necesita que el volumen esté montado.

Los CSS/JS originales siguen siendo legibles. El build genera `build/static/*.gz` y `build/assets.json`; producción negocia gzip según `Accept-Encoding` y devuelve `Vary` y ETag por variante. Desarrollo sirve el fuente. Se mantiene revalidación de caché para que una actualización no deje archivos antiguos activos.

ProxyFix confía en una capa de proxy para esquema e IP, y sólo se activa en producción. Debe ajustarse si cambia la topología: confiar en cabeceras de un cliente directo no es seguro. El host se valida sin confiar en X-Forwarded-Host. [Configuración de ProxyFix](https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/).

La aplicación redirige HTTP a HTTPS, activa cookies Secure y HSTS en producción. La ruta de salud permite la comprobación interna HTTP. La verificación de Origin de CSRF usa el esquema/host efectivo después del proxy. Los logs de Gunicorn excluyen query strings y los logs de aplicación omiten cuerpos y errores SQL con datos privados.

Conservar `.gitattributes`: desactiva la conversión de saltos de línea en `sql/*.sql`, para que Windows y Linux mantengan exactamente los bytes y checksums de las migraciones ya aplicadas. No reformatear los SQL existentes antes de desplegar.

## Servicio de correo

Usar el mismo código y `railway.worker.json` como configuración del servicio worker. Inicio: `python run.py worker`. Configurar las referencias MySQL, `VETCARE_SECRET_KEY`, `VETCARE_PRODUCTION=true`, `VETCARE_SERVICE=worker` y las variables SMTP documentadas en README. No necesita dominio público ni volumen para fotografías.

El servicio web guarda las notificaciones; el worker es necesario para enviarlas. El monitor de agenda funciona dentro del servidor web y no necesita este worker.

**Gmail y planes:** la documentación actual de Railway habilita SMTP sólo en Pro o superior; Free, Trial y Hobby bloquean los puertos SMTP. Mantener Gmail por SMTP requiere verificar el plan del servicio y redeplegar después de habilitarlo. La configuración SMTP local no demuestra que esos puertos estén disponibles en la nube. No se cambió el proveedor ni se contrataron servicios. [Regla oficial de correo saliente](https://docs.railway.com/networking/outbound-networking).

El worker reclama notificaciones mediante `FOR UPDATE SKIP LOCKED`. SMTP ocurre fuera de una transacción de negocio. Un estado `Enviando` tras caída del proceso requiere contrastar la entrega con el proveedor antes de reintentar. No se reinicia automáticamente porque podría duplicar un mensaje ya aceptado.

## Validación antes de cambiar producción

- Construir y ejecutar Docker con motor activo. Revisar el lock/resolución de dependencias de la imagen Linux y confirmar ausencia de Django.
- Probar HTTPS, cookies Secure, login con la cuenta real, logout y rutas protegidas en el dominio nuevo.
- Consultar los registros anteriores y comparar conteos/filas con el respaldo antes de habilitar escrituras de usuarios.
- Completar una cita, su notificación real, factura y descarga PDF; revisar el flujo de adopciones con datos autorizados de prueba.
- Subir una foto, reiniciar/desplegar de nuevo y comprobar que persiste en el volumen.
- Medir tiempos y consumo en la red privada. El rendimiento desde el PC no representa la latencia dentro de Railway.

No borrar el servicio anterior ni sus respaldos durante la validación. Las tablas históricas se conservan y las nuevas son aditivas. Antes de activar usuarios, preparar también el rollback de autenticación: los hashes Argon2 nativos creados por la versión nueva requieren un verificador compatible o restablecimiento controlado al volver a la versión anterior. El estado actual conserva intactos los hashes reales; consultar la sección Recuperación de `MIGRACION_WSGI.md`.
