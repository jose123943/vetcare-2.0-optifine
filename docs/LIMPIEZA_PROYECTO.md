# Limpieza y reglas de agenda · 17 de noviembre de 2026

La aplicación mantiene su arquitectura Python WSGI, HTML/CSS/JavaScript y MySQL. La revisión de referencias retiró archivos heredados sin uso y un paquete generado que había quedado desactualizado.

## Archivos retirados

| Archivo | Motivo |
|---|---|
| `frontend/assets/login/css/styles.css` | Estilo de la interfaz anterior; ninguna página ni script lo carga. |
| `frontend/assets/pagInicio/css/styles.css` | Estilo antiguo sustituido por `app.css` y `v2.css`; sin referencias. |
| `frontend/assets/login/imgs/huella.png` | Copia idéntica sin referencias; se mantiene la versión utilizada por favicon, PDF y pruebas en `pagInicio/imgs/`. |
| `frontend/assets/login/imgs/security_logo.png` | Imagen antigua que no utiliza la interfaz actual. |
| `dist/VetCare-WSGI-railway.zip` | Distribución generada anterior a estos cambios. Puede recrearse con `scripts/empaquetar_wsgi.py`. |

Antes de retirarlos se creó un archivo ZIP privado, se verificó su integridad y se comparó el SHA-256 de cada archivo recuperado. El nombre del respaldo y su manifiesto están en `limpieza-archivos.json`. El respaldo se conserva fuera del proyecto, en `.codex/backups/vetcare` del usuario.

La eliminación de las cachés locales `__pycache__` del código propio y `.ruff_cache` fue bloqueada por la revisión automática de herramientas, incluso al limitar los destinos a rutas verificadas del proyecto. El motivo devuelto fue bloqueo de política, sin detalle adicional. Esas cachés permanecen excluidas de Git y no afectan el funcionamiento. Se mantienen el entorno virtual, `.env`, fotografías, migraciones SQL aplicadas, pruebas y documentación de recuperación.

## Dependencias

La auditoría de importaciones y puntos de entrada no detectó dependencias declaradas de ejecución que puedan eliminarse sin perder funciones:

| Dependencia | Uso |
|---|---|
| Werkzeug / Waitress | HTTP y servidor en Windows. |
| Gunicorn | Servidor y monitor por proceso en Linux; instalación condicional. |
| PyMySQL con RSA | Conexión y autenticación MySQL. |
| argon2-cffi / passlib | Contraseñas actuales y compatibilidad con cuentas heredadas. |
| itsdangerous | Verificación de resultados privados de adopciones de versiones anteriores. |
| python-dotenv | Configuración privada local. |
| tzdata | Zona horaria de Colombia en Windows. |
| ReportLab / Pillow | Facturas PDF y procesamiento de fotografías. |
| pypdf, desarrollo | Lectura y comprobación de PDF en las pruebas. |

No se actualizaron versiones ni se eliminaron dependencias transitivas a ciegas. El monitor de citas utiliza `threading` de la biblioteca estándar.

## Comportamiento actualizado

- En **Clientes y mascotas** y **Agendar cita**, el buscador despliega propietarios al recibir el foco, filtra por lo escrito y permite seleccionar con ratón o flechas/Enter. Escape cierra la lista. Los documentos e identificadores distinguen nombres repetidos.
- Elegir un propietario en Clientes y mascotas filtra por su identificador exacto. Escribir de nuevo vuelve a la búsqueda libre de paciente, nombre, documento, teléfono o correo. La selección en Agendar sólo carga los pacientes de esa persona.
- Una cita nueva sólo admite **Programada**, también al validar la API. Desde su detalle puede editarse o cancelarse conservando historial.
- Al alcanzar `fecha + hora + duración`, pasa a **Atendida**. El servidor revisa cada 15 segundos, con hora `America/Bogota`, sin depender de Gmail. Consultar agenda, detalle o resumen sincroniza los estados inmediatamente. Las canceladas se conservan.
- La agenda visible consulta cambios cada 15 segundos, conserva las páginas cargadas y evita refrescar mientras un modal está abierto. El cambio automático no genera correos adicionales.
- El método de pago es un selector de **Transferencia**, **Efectivo** o **Tarjeta**, tanto al crear la factura como al actualizarla. Python valida las mismas opciones y el PDF muestra el método guardado.

## Vaciar los datos operativos

Detener el servidor y el worker antes de aplicar una limpieza. Este comando sólo muestra conteos:

```powershell
.\.venv-wsgi\Scripts\python.exe scripts/limpiar_datos.py
```

La siguiente opción explícita respalda y vacía datos operativos, sin cargar ejemplos:

```powershell
.\.venv-wsgi\Scripts\python.exe scripts/limpiar_datos.py --aplicar
```

El respaldo completo incluye estructura y datos, se verifica después de escribirlo y queda fuera del repositorio. La limpieza usa una transacción, respeta claves foráneas y conserva las filas completas, contraseñas y permisos de **todos** los superusuarios. Mantiene el cuestionario y los metadatos técnicos necesarios. Cualquier fallo anterior al COMMIT revierte la limpieza.

El resultado de la limpieza operativa autorizada se registra en `limpieza-base.json`. Los informes de la demostración anterior describen datos históricos; no vuelven a cargar datos al iniciar.

La limpieza ya se aplicó. `limpieza-verificacion-real.json` confirma datos operativos vacíos, dos superusuarios con sus filas completas y permisos intactos, y diez tablas de configuración idénticas al respaldo. Pasaron las 55 pruebas automatizadas y el recorrido de navegador de propietarios, agenda y pagos.
