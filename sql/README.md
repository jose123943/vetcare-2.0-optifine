# Grupos del esquema SQL

Estos archivos están registrados con SHA-256 en `vc_schema_migration`. No se modifican ni se les añaden comentarios después de aplicarlos. Las explicaciones se mantienen aquí para conservar su integridad entre Windows y Linux.

| Archivo | Grupos de código y responsabilidad |
|---|---|
| `000_esquema_existente.sql` | Estructura heredada: usuarios, permisos, clientes, mascotas, empleados/veterinarios, citas, vacunas, tratamientos, facturas y adopciones. Incluye claves foráneas, restricciones e índices. |
| `001_wsgi.sql` | Sesiones de la aplicación, límites de login, registro de migraciones y adaptaciones aditivas para WSGI. Conserva las tablas anteriores. |
| `002_sesion_programa.sql` | Vincula sesiones autenticadas con una ejecución del programa; al revocar el token se elimina el vínculo por clave foránea. |

`auth_*` contiene identidad y permisos. Las tablas de clínica relacionan paciente → propietario → cita → profesional y facturación. `adopciones_*` conserva catálogo, versiones, respuestas, evaluación, revisión y entrega. `pagInicio_operacion` evita duplicar escrituras y `pagInicio_notificacion` permite enviar correos fuera de la petición web. `vc_*` mantiene el control técnico de la aplicación.

`python run.py migrate` aplica únicamente archivos pendientes mediante un bloqueo de esquema y valida los checksums de los anteriores. No vacía datos. La limpieza y los ejemplos son comandos administrativos separados.
