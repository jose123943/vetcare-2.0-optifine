# VetCare: migración a Python WSGI + MySQL

## Arquitectura

El mismo producto conserva sus módulos, estilos, rutas compatibles e identificadores. El entorno `.venv-wsgi` ejecuta Python sin Django, Flask ni FastAPI. Werkzeug aporta análisis HTTP, respuestas, rutas y acceso seguro a archivos; no se utiliza un framework completo. Waitress atiende Windows y Gunicorn atiende el contenedor Linux. No se usan servidores de desarrollo para atender usuarios.

| Carpeta | Responsabilidad |
|---|---|
| `frontend/pages` | HTML estático de acceso, dashboard, catálogo y resultado |
| `frontend/assets` | CSS, imágenes y JavaScript conservados; bootstrap y configuración propios |
| `vetcare/application.py` | Rutas HTTP, permisos, errores e idempotencia |
| `vetcare/http.py` | Lectura JSON/formularios, cookies y paginación |
| `vetcare/config.py` | Variables privadas y validaciones del entorno |
| `vetcare/security.py` | Sesiones, CSRF, cuentas antiguas y control de intentos |
| `vetcare/db.py` | Pool PyMySQL, SQL parametrizado y transacciones |
| `vetcare/services` | Clínica, facturación, adopciones, cuentas, correo y PDF |
| `sql` | DDL versionado y aditivo; no contiene filas privadas |
| `tests` | Integración HTTP con una base MySQL aislada |
| `run.py` | Arranque, comprobación, migración SQL, worker y respaldo |

PyMySQL evita compiladores/controladores nativos en Windows y permite parámetros `%s`, transacciones, cursores y RSA mediante `cryptography`. Argon2-cffi y Passlib verifican contraseñas sin implementar criptografía propia. ItsDangerous verifica únicamente las firmas de sesiones antiguas que protegen resultados de adopciones. ReportLab genera documentos; Pillow valida, limita y vuelve a codificar fotos a WebP.

## Inventario funcional y equivalencias

`inventario_wsgi.json` conserva las columnas, cantidades, claves foráneas y rutas originales. `endpoints_wsgi.json` enumera todos los métodos/rutas nuevos y sus controles. Las rutas `/inicio/api/…` y `/adopciones/api/…` continúan operativas para la interfaz conservada; se añaden alias `/api/…` para los clientes HTTP nuevos.

| Función / rutas originales | Sustitución | Tablas / relaciones | Validación y permisos |
|---|---|---|---|
| `/`, `/salir/`, `/inicio/` | HTML + `/api/auth/login`, `/api/auth/logout`, `/api/session` | `auth_user`, `vc_session`, `vc_login_bucket` | Staff activo, sesión expirable, CSRF, bloqueo de intentos, rotación de sesión |
| `/inicio/api/dashboard/` | Mismo endpoint SQL | Cliente, mascota, cita, veterinario, vacunas | Staff; estadísticas reales y todas las citas pendientes |
| `/inicio/api/clientes/` | Mismo + `GET /api/clientes`, `GET/PUT/DELETE /api/clientes/<id>` | `cliente` | Documento único, longitudes, email, estados; eliminación sin dependencias |
| `/inicio/api/registrar/cliente-mascota/` | Mismo + `POST /api/clientes` | `cliente` → `mascota` | De 1 a 50 mascotas; validación completa y transacción única |
| `/inicio/api/clientes/<id>/mascotas/`, `agregar-mascota/` | Mismos + `GET/POST /api/clientes/<id>/mascotas` | FK mascota-cliente | Propietario existente; alta sin duplicar cliente |
| `mascotas/`, `mascotas-selector/`, `detalle-mascota/<id>/` | Mismos + `GET /api/mascotas[/<id>]` | Mascota + cliente | Búsqueda parametrizada, selector e historial; staff |
| `editar-registro/`, `eliminar-registro/<id>/` | Mismos + `DELETE /api/mascotas/<id>` | Mascota + propietario + historiales | Edición conjunta; comprueba pertenencia; no elimina historiales |
| `cargar-datos-agenda/`, `veterinarios/guardar/` | Mismos + `GET/POST/PUT /api/veterinarios` | `empleado` → `veterinario` | Datos profesionales y FK; eliminación adicional sin citas |
| `citas/`, `citas/<id>/`, `citas-mascota/<id>/` | Mismos + `GET /api/citas[/<id>]`, `/pendientes` | Cita → mascota → cliente; veterinario → empleado | Staff, paginación, detalles y notificaciones |
| `registrar/cita/`, `citas/<id>/editar/` | Mismos + `POST /api/citas`, `PUT /api/citas/<id>` | Cita + outbox | Cliente dueño de mascota, duración válida, estados y bloqueo de veterinarios para evitar solapamientos |
| `vacunas-mascota/<id>/`, `registrar-vacuna/` | Mismos + `POST /api/vacunas` | `historial_de_vacunas` → mascota | Fechas coherentes, lote, paciente existente |
| `tratamientos-mascota/<id>/`, `registrar-tratamiento/` | Mismos + `POST /api/tratamientos` | `tratamiento` → cita → mascota | Campos y longitudes, cita real; historial conservado |
| `resumen-facturas/`, `listar-facturas/`, `detalle-factura/<id>/` | Mismos + `GET /api/facturas[/<id>]` | Factura → cita/cliente/usuario; detalle → factura | Staff; estados, filtros, totales SQL y consulta histórica |
| `datos-factura/`, `registrar-factura/`, `actualizar-estado-factura/` | Mismos + `POST /api/facturas` | Factura + detalle | Decimal exacto, cantidades enteras, servicios reales; administrador desde la sesión |
| `facturas/<id>/pdf/` | Mismo + `/api/facturas/<id>/pdf` | Factura + detalle + paciente | Documento multipágina con importes reales; históricos sin desglose identificados |
| `notificaciones/`, `notificaciones/<id>/reintentar/` | Mismos + `python run.py worker` | `pagInicio_notificacion` → cita | Cola transaccional, SKIP LOCKED, SMTP fuera de HTTP; errores sin secretos |
| `/adopciones/`, `api/catalogo/`, `api/cuestionario/`, `fotos/<id>/` | Mismos + alias `/api/adopciones/…` | MascotaAdopcion + cuestionario/criterios/preguntas/opciones | Catálogo público paginado, sin datos de solicitantes ni valores de respuesta |
| `api/mascotas/<id>/solicitar/`, `solicitud/<uuid>/` | Mismos + resultado JSON | Solicitud → mascota/cuestionario; respuestas → pregunta/opción | Mayor de edad, consentimiento, encuesta completa; propietario de sesión y límites de envío |
| `api/admin/mascotas/guardar/`, `foto/` | Mismos | MascotaAdopcion → paciente opcional | Staff, control de estados, fotos limitadas y metadatos eliminados |
| `api/admin/solicitudes/`, detalle y `revisar/` | Mismos | Solicitud + revisión + entrega | Staff, bienestar confirmado; puntuación exacta ≥67; una entrega por mascota/solicitud |
| `api/admin/cuestionario/pesos/`, antiguo Admin de preguntas | Configuración propia + API de versiones | Cuestionario → criterios → preguntas → opciones | Pesos suman 100; borradores editables; versiones utilizadas inmutables |
| Antiguo Admin de usuarios | Configuración → Cuentas + `/api/admin/usuarios` | `auth_user` | Sólo superadministrador; Argon2, revocación de sesiones y protección de la cuenta propia |

Todos los endpoints administrativos requieren staff activo, aunque se conozca un ID. Las escrituras requieren CSRF y, excepto autenticación y solicitud pública, `Idempotency-Key`. La solicitud pública tiene su propia clave única y verifica además al propietario de sesión. No se usan identificadores recibidos del cliente como nombres de tablas o columnas.

Las tablas `adopcion` y `evaluacion_adopcion` son antecedentes de una implementación previa sin rutas activas en el inventario. Sus filas, restricciones e identificadores se mantienen y se pueden consultar desde Configuración → Antecedentes conservados y `/api/admin/historico/adopciones[/<id>]`, con acceso staff. Sus resultados se muestran sin recalcularlos con el umbral del catálogo actual. Las tablas de grupos/permisos, migraciones y auditoría originales permanecen en MySQL; su existencia no implica dependencia del framework. Las cuentas del sistema conservan la regla de acceso staff/superusuario que tenían las API anteriores.

## Cómo viajan los datos: HTML → JavaScript → Python → MySQL

1. Un formulario HTML recoge el propietario y una lista dinámica de mascotas. El CSS controla la presentación, sin participar en la persistencia.
2. JavaScript valida las restricciones del navegador, desactiva botones y construye `{nombre, documento, …, mascotas:[…]}`. `fetch()` envía JSON con `Content-Type`, `X-CSRFToken` e `Idempotency-Key`. El navegador adjunta la cookie HttpOnly de sesión sin exponer su valor al código de la página.
3. El servidor WSGI interpreta HTTP con Werkzeug. Comprueba host, sesión, permisos, CSRF y método. El servicio de clínica repite la validación: nunca confía sólo en el navegador.
4. El acceso SQL reserva una conexión del pool, inicia transacción e inserta la clave única de operación. Inserta el cliente y las mascotas con parámetros `%s`, conservando la FK del propietario.
5. La respuesta JSON y los cambios se confirman juntos. Si falla cualquier mascota, se revierte toda la operación. Si llega la misma clave, se devuelve la respuesta guardada; si cambian los datos, devuelve 409.
6. JavaScript interpreta el resultado, muestra la confirmación y actualiza la sección necesaria. Una respuesta de error conserva los campos y permite corregirlos; ante error de red reutiliza la clave.

## Sesiones y contraseñas

La cuenta real inventariada usaba `pbkdf2_sha256`. Passlib verifica ese formato y PBKDF2-SHA1/Argon2 heredados. Al iniciar sesión correctamente se actualiza únicamente ese hash a Argon2. Las cuentas existentes no se recrean, ni se pide cambiar sus contraseñas por la migración. La compatibilidad se prueba con un vector producido por el sistema anterior y un usuario sintético con ese mismo formato; la contraseña personal del administrador real no está disponible para una prueba manual desde esta sesión.

La cookie `vetcare_sid` contiene 32 bytes aleatorios codificados y su hash se almacena en MySQL. Desde la actualización del 17 de noviembre, el acceso autenticado se vincula a la ejecución del servidor en `vc_session_scope` y se conserva hasta cerrar sesión o cambiar esa ejecución; se eliminó el límite fijo de ocho horas para administradores. Las cookies siguen siendo de sesión, con HttpOnly/SameSite=Lax y Secure en producción. Sólo las sesiones anónimas conservan el vencimiento de ocho horas. La cookie CSRF se compara con su hash guardado y se valida el Origin cuando existe. El logout revoca la sesión y su vínculo de ejecución. Los intentos se cuentan en MySQL por cuenta y dirección, compartidos entre procesos.

Se conserva el valor privado de la clave de firma anterior, renombrado `VETCARE_SECRET_KEY`. Esto permite verificar sesiones antiguas de visitantes para mantener acceso a sus resultados privados. Las sesiones administrativas antiguas requieren iniciar sesión otra vez. No se interpreta ni confía en el usuario administrativo de una sesión antigua.

## Integridad, transacciones y rendimiento

Antes de escribir se creó ZIP recuperable íntegro y respaldo lógico consistente de las 33 tablas fuera del repositorio. `wsgi_integridad_completa.json` compara cada fila y columna con ese respaldo sin publicar datos. Las migraciones SQL sólo añaden tablas nuevas de sesiones, intentos y seguimiento del esquema. El DDL original usa `CREATE TABLE IF NOT EXISTS`, no reinicia datos ni contadores en tablas existentes. El ejecutor usa un lock de esquema y comprueba SHA-256 para no modificar una migración aplicada.

Las transacciones de negocio usan READ COMMITTED, bloqueos de veterinario ordenados y comparación de horarios en segundos, incluyendo citas adyacentes. La clave única de operaciones evita reenvíos concurrentes. Adopciones bloquea la mascota antes de autorizar o entregar; las restricciones únicas son una segunda defensa. La regla del 67 % usa fracciones exactas, sin redondear para aprobar. Los snapshots y porcentajes anteriores no se recalculan.

El pool reutiliza conexiones por proceso, reconecta sólo antes de ejecutar operaciones y no reenvía escrituras tras un fallo. Listados usan `LIMIT tamaño+1` sin un COUNT adicional; no hay consultas por cada fila. Cada proceso admite ocho conexiones por defecto: dimensionar `DB_POOL_SIZE × workers` según el límite de MySQL. `Server-Timing` mide el tiempo total y `X-VetCare-SQL-Queries` cuenta las consultas de aplicación, sin exponer SQL o parámetros.

Las mediciones comparativas se guardan con muestras y contexto. Eliminar un framework no garantiza una menor latencia: desde Windows domina la conexión pública a Railway. La latencia en la red privada del despliegue requiere medición en Railway.

## Correo, archivos y límites conocidos

La cola de correo se confirma junto con la cita. El worker utiliza SMTP con TLS/SSL y registra sólo la clase del fallo. La notificación incluye texto y HTML escapado. Si un worker muere después de que el proveedor acepte un mensaje y antes de guardar el estado, queda `Enviando`; se requiere contrastarlo con el proveedor antes de reintentar, para evitar duplicados. No se promete entrega exactamente una vez por SMTP.

Las fotografías se guardan en MEDIA_ROOT, con nombres aleatorios, lectura segura y sin metadatos originales. En Railway ese directorio debe estar en un volumen persistente; los PDF se regeneran con los datos guardados. Un archivo creado justo antes de un rollback podría quedar huérfano, sin acceso público asociado; no se borran fotos históricas automáticamente.

La política CSP conserva scripts/estilos inline por compatibilidad con la interfaz existente; no debe describirse como CSP estricta. Todo texto de usuarios se escapa en HTML/PDF/correos. El log evita cuerpos de solicitudes, parámetros SQL, contraseñas y trazas con datos privados.

## Recuperación

Los respaldos privados están en `C:\Users\USER\.codex\backups\vetcare`. El ZIP `django_completo_20261114_214524.zip` fue verificado con 8.741 archivos; el gzip `vetcare_20261115_024535.json.gz` contiene las 33 tablas antes de migrar. No forman parte del paquete compartido.

Para recuperar el programa anterior, extraer el ZIP en una carpeta nueva y usar su configuración privada. Las tablas anteriores permanecen estructuralmente compatibles, porque las tablas nuevas son aditivas. La comparación de las 33 tablas idénticas corresponde a la migración inicial. El 17 de noviembre el propietario solicitó sustituir los datos operativos por ejemplos, conservando los superusuarios y sus hashes; esa operación tiene respaldos privados nuevos y su propio informe en `docs/demostracion-carga.json`.

Después de que una cuenta real inicie sesión en la nueva versión, su hash se actualiza a Argon2 en formato nativo. La versión anterior no reconoce directamente ese formato. Antes de un rollback posterior debe prepararse un verificador compatible en la versión recuperada o un restablecimiento controlado de esas cuentas; no asumir que basta cambiar el código después de activar usuarios. No sobrescribir toda la tabla de usuarios ni restaurar automáticamente la base completa, porque eso podría perder cambios posteriores.

Si hubiera un incidente de datos, restaurar primero el respaldo en una base nueva aislada y verificar sus conteos antes de cualquier sustitución. No ejecutar DROP/TRUNCATE sobre `railway`.
