# VetCare: funciones, pestañas y funcionamiento

Guía de la aplicación Python WSGI + MySQL, actualizada el **17 de noviembre de 2026**. Los registros de demostración son ficticios y no constituyen indicaciones clínicas, certificados ni facturas electrónicas.

El [mapa del proyecto](docs/ESTRUCTURA.md) explica las carpetas actuales. El código incluye comentarios sobre funciones y bloques; los informes y capturas están en `docs/evidencias/`. La [guía de Railway](docs/RAILWAY.md) describe la preparación y los requisitos de publicación.

**Actualización:** la última limpieza deja la base operativa vacía, conservando todos los superusuarios y la configuración necesaria. La demostración descrita más abajo es opcional y no se carga al iniciar. Véase [limpieza del proyecto y reglas actuales](docs/LIMPIEZA_PROYECTO.md).

## 1. Abrir el programa

En la terminal PowerShell de Visual Studio Code, desde la carpeta del proyecto:

```powershell
.\.venv-wsgi\Scripts\python.exe run.py check
.\.venv-wsgi\Scripts\python.exe run.py serve
```

Abrir `http://127.0.0.1:8000`. El catálogo público está en `http://127.0.0.1:8000/adopciones/`. Para detener el servidor, pulsar Ctrl+C en su terminal.

La aplicación utiliza Python, Werkzeug para HTTP/WSGI, Waitress en Windows, SQL parametrizado con PyMySQL y MySQL en Railway. HTML, CSS y JavaScript forman la interfaz. No utiliza Django, Flask, FastAPI ni un framework de frontend.

## 2. Inicio de sesión y permisos

El formulario valida usuario y contraseña contra `auth_user`. Los superusuarios conservados mantienen sus datos; se reconocen hashes heredados y los nuevos se guardan con Argon2. No se utiliza la contraseña de MySQL para acceder al dashboard.

- **Superusuario:** administra la clínica, adopciones, cuestionarios y cuentas.
- **Personal administrativo activo:** accede a las funciones de clínica y adopciones; no administra cuentas de otros usuarios.
- **Visitante:** consulta el catálogo y realiza una encuesta de adopción. No puede acceder a información clínica ni a solicitudes de otras personas.

### Duración de la sesión

La sesión autenticada **ya no vence automáticamente a las ocho horas**. Permanece válida durante la misma ejecución del servidor. `vc_session` guarda el hash del token y `vc_session_scope` lo vincula a la ejecución que lo creó.

**Cerrar sesión** revoca el token y elimina las cookies. Al detener y volver a iniciar el servidor local cambia la identidad de ejecución: las cookies anteriores ya no autentican. El usuario debe entrar de nuevo. Los workers de Gunicorn comparten una identidad por ejecución; en Railway se utiliza la identidad del despliegue para compartirla entre réplicas del mismo despliegue. [Variables proporcionadas por Railway](https://docs.railway.com/variables/reference).

Las cookies son de sesión, sin `Max-Age` ni fecha de persistencia. El navegador puede eliminarlas al cerrarse; algunos navegadores restauran cookies al recuperar ventanas, por lo que la revocación garantizada se produce con **Cerrar sesión** o al cambiar la ejecución del servidor. Las sesiones anónimas del catálogo conservan una caducidad de ocho horas para los resultados privados.

Se mantienen HttpOnly, SameSite, CSRF, comprobación de permisos en el servidor y bloqueo temporal de intentos fallidos. En producción las cookies usan Secure y HTTPS.

## 3. Mapa de pestañas

| Pestaña | Ruta interna | Objetivo |
|---|---|---|
| Resumen | `#dashboard` | Indicadores y citas pendientes |
| Nuevo cliente | `#registrar` | Propietario con una o varias mascotas |
| Clientes y mascotas | `#consultar` | Buscar, editar, agregar pacientes y consultar fichas |
| Agendar cita | `#agendar` | Crear una cita seleccionando propietario, mascota y veterinario |
| Agenda completa | `#citas` | Consultar y modificar citas |
| Veterinarios | `#veterinarios` | Registrar, editar y retirar profesionales sin historial |
| Salud e historial | `#vacunacion` | Vacunas y tratamientos por paciente |
| Facturas y reportes | `#reportes` | Totales, documentos, servicios, pagos y PDF |
| Notificaciones | `#correos` | Estado de los correos y reintento de fallos |
| Gestión de adopciones | `#adopciones` | Mascotas disponibles, encuestas, solicitudes y entrega |
| Configuración | `#configuracion` | Cuestionarios, cuentas y antecedentes |
| Catálogo público | `/adopciones/` | Consulta y encuesta para aspirantes a adoptar |

El menú cambia el contenido central mediante JavaScript. Cada sección pide JSON a la API y actualiza su tabla o formulario sin recargar toda la aplicación.

## 4. Resumen

Muestra citas del día, clientes activos, citas pendientes y vacunas cuya fecha de vencimiento ya se alcanzó. La tabla de pendientes incluye también citas de otras fechas; las vencidas se identifican visualmente y se conserva su estado hasta que el equipo lo cambie.

**Agendar cita** abre el formulario de agenda. **Ver detalle** permite consultar paciente, propietario, profesional, fecha, motivo, observaciones y notificaciones. Los indicadores provienen de MySQL y cambian al guardar registros.

## 5. Nuevo cliente

Se introducen nombres, apellidos, documento, teléfono, dirección y correo opcional del propietario. El documento identifica de forma única a cada cliente nuevo.

**Agregar mascota** incorpora otra ficha. **Aplicar cantidad** prepara entre una y 50 fichas. Cada mascota incluye nombre, especie, raza, sexo, edad, peso y observaciones. **Quitar** retira una ficha antes de guardar.

**Registrar cliente y mascotas** valida todos los campos, crea un solo propietario y asocia sus pacientes en una transacción. Si falla una ficha no se guarda parcialmente la familia. El botón se bloquea durante el envío y una clave de idempotencia evita duplicar la operación por reintentos de red.

## 6. Clientes y mascotas

El buscador localiza pacientes por mascota, nombre del propietario, documento, teléfono o correo. **Cargar más pacientes** obtiene la página siguiente.

Al hacer clic en **Buscar** aparece una lista de propietarios. Se puede escribir para filtrar o seleccionar con ratón y con flechas/Enter; Escape cierra la lista. Elegir un propietario muestra sus mascotas por su identificador exacto, incluso cuando dos personas tienen el mismo nombre. Escribir de nuevo permite volver a buscar libremente por paciente u otros datos.

**Ficha / editar** abre los datos del propietario y el paciente seleccionado. **Actualizar registro** guarda ambos; las mascotas siguen perteneciendo al mismo cliente. Se puede activar o desactivar al propietario sin eliminar sus historiales.

**Otra mascota** registra un paciente para un propietario existente. **Ver propietarios** permite consultar clientes aunque no tengan mascotas, editar sólo sus datos o añadirles un paciente.

Las eliminaciones se validan también en el servidor: una mascota con citas, vacunas o relaciones de adopción se conserva. Un cliente con mascotas o facturas no puede eliminarse; puede marcarse inactivo. Otras relaciones históricas también están protegidas por claves foráneas.

## 7. Agendar cita

1. Buscar al propietario por nombre, documento o teléfono.
2. Seleccionarlo para cargar exclusivamente sus mascotas.
3. Elegir paciente y veterinario.
4. Introducir fecha, hora, duración, motivo y observaciones. El único estado inicial es **Programada**.
5. Pulsar **Registrar cita**.

El servidor comprueba la pertenencia del paciente y evita solapamientos para el mismo veterinario. Dos citas pueden ser adyacentes cuando una empieza exactamente al terminar la anterior. La cita debe terminar el mismo día y durar entre cinco y 480 minutos.

El buscador despliega propietarios al recibir el foco, sin exigir caracteres previos, y conserva la búsqueda por nombre, documento, teléfono o correo. Sólo carga los pacientes del propietario elegido.

Al crear o modificar realmente la cita se guarda una notificación junto con el cambio. El correo no se envía dentro de esa petición HTTP. Los datos de demostración utilizan direcciones `.invalid`: sus notificaciones se marcan **Demostración** y nunca entran en la cola de envío real.

## 8. Agenda completa

Lista primero las citas de hoy y futuras, de la fecha y hora más cercana a la más lejana. Las citas pasadas aparecen al final, de la más reciente a la más antigua. Este mismo orden se utiliza en el resumen y en todos los desplegables de citas, incluidos tratamientos y facturación; sus opciones muestran también la hora. El orden se aplica antes de paginar, independientemente de cuándo se creó cada registro. **Ver detalle → Editar / cambiar estado** abre los mismos controles del agendamiento.

Las citas nuevas se guardan como **Programada**. Al alcanzar su fecha, hora y duración pasan automáticamente a **Atendida**, usando la hora de Colombia. El monitor del servidor revisa cada 15 segundos, sin depender de Gmail, y consultar agenda/detalle/resumen también sincroniza los estados. La agenda visible se actualiza cada 15 segundos sin recargar toda la página, conserva sus páginas y pausa la actualización durante un modal.

Desde el detalle se puede reprogramar, marcar atendida o cancelar. Las **Canceladas** conservan su estado e historial. El cambio automático no crea notificaciones adicionales. Los estados antiguos Pendiente/Confirmada se reconocen sólo por compatibilidad con datos previos; no se ofrecen al crear. Los reenvíos de una misma operación no crean citas adicionales.

## 9. Veterinarios

**Registrar veterinario** solicita nombres, apellidos, teléfono y especialidad. Se crea su registro de empleado y su registro de veterinario relacionados por el mismo identificador.

**Editar** modifica los datos profesionales. **Eliminar veterinario sin citas** sólo funciona cuando no existen dependencias que deban conservarse. Si ya tiene citas o antecedentes, el servidor rechaza la eliminación.

## 10. Salud e historial

Primero se selecciona un paciente. La aplicación consulta sus vacunas, tratamientos y citas relacionadas.

**Registrar vacuna** guarda nombre, lote, aplicación y vencimiento. El vencimiento no puede ser anterior a la aplicación; el listado calcula los días restantes.

**Registrar tratamiento** requiere una cita del paciente e incluye descripción, medicamento, dosis, duración y fecha de inicio. Los ejemplos cargados son ficticios, sin pautas médicas utilizables. Esta pestaña conserva las relaciones de cada registro con su paciente y cita.

## 11. Facturas y reportes

Las tarjetas muestran ingresos cobrados, importe pendiente, cantidad total y facturas pagadas. El filtro de estado y la paginación permiten explorar el historial.

**Nueva factura** selecciona una cita y obtiene su cliente/paciente. Cada servicio incluye descripción, cantidad y precio. **Agregar servicio** añade líneas; **Quitar servicio** las retira antes de guardar.

El navegador muestra una estimación, pero Python vuelve a calcular con Decimal: `total = suma(cantidad × precio) − descuento + impuesto`. No se aceptan importes negativos, cantidades fraccionarias ni descuentos superiores al subtotal. Factura y líneas se confirman juntas.

**Detalle** muestra el desglose, permite cambiar el estado de pago y descargar el PDF. **Descargar factura PDF** genera el documento con datos guardados; no exige un archivo PDF previamente subido. Los documentos son de gestión interna y no equivalen a facturación electrónica autorizada.

El **Método de pago** es un menú de **Transferencia**, **Efectivo** o **Tarjeta**, tanto en Nueva factura como en su detalle. Se guarda y valida en el servidor y se muestra en el PDF.

## 12. Notificaciones por correo

Muestra cita, fecha de creación, estado, intentos y diagnóstico. **Actualizar** consulta los estados nuevos. **Reintentar** devuelve un aviso fallido a la cola cuando ya se ha corregido la causa.

| Estado | Significado |
|---|---|
| Pendiente | Espera al worker |
| Enviando | Un worker la ha reclamado |
| Enviada | El servidor SMTP aceptó el mensaje; no acredita lectura ni ubicación en la bandeja |
| Fallida | El intento no terminó correctamente; se muestra un diagnóstico seguro |
| Sin correo | El cliente no tiene dirección registrada |
| Demostración | Ejemplo ficticio que no se envía a Gmail |

El proceso de envío se inicia en otra terminal con `python run.py worker`, usando el Python de `.venv-wsgi`. Gmail se configura con `scripts/configurar_gmail.py`: solicita la dirección remitente y una contraseña de aplicación de forma oculta, valida TLS/autenticación y guarda los datos en el `.env` privado. No comparte la contraseña de MySQL ni muestra secretos en la tabla de errores.

El destinatario se toma del **cliente de la cita**, no del correo del administrador. Se guarda con la notificación. Un worker antiguo puede conservar una configuración anterior: detenerlo antes de iniciar otro con nuevas credenciales. Las notificaciones se reclaman con `FOR UPDATE SKIP LOCKED` para evitar que dos workers procesen la misma a la vez.

## 13. Gestión de adopciones y botón de encuesta

### Mascotas disponibles

**Nueva mascota** registra nombre, especie, raza, sexo, edad aproximada, peso, historia, personalidad, salud, vacunas, esterilización y necesidades. El vínculo a un paciente clínico es opcional.

**Editar** mantiene la ficha. **Fotografía** acepta JPEG, PNG o WebP de hasta cinco MB; se valida, limita y convierte a WebP sin metadatos originales. Las fotos se guardan en `MEDIA_ROOT`.

### Realizar la encuesta con la persona interesada

Cada tarjeta disponible incluye **Realizar encuesta**. Abre en una pestaña nueva el catálogo con la encuesta de **esa mascota** ya seleccionada. La dirección tiene el formato `/adopciones/?mascota=ID#encuesta` y no incluye datos personales ni credenciales.

El botón general **Realizar encuesta** abre el catálogo para elegir una mascota. El visitante también puede pulsar el botón de la tarjeta pública. El personal puede acompañar a la persona en el llenado; no es necesario crearle una cuenta administrativa.

1. Introducir datos del solicitante y consentimiento.
2. Contestar las preguntas por criterio, avanzando con **Continuar**.
3. Revisar pasos anteriores con **Anterior**.
4. Pulsar **Enviar evaluación** una sola vez.
5. Consultar el porcentaje, resultado y recomendaciones.

El backend comprueba todas las preguntas de la versión indicada y calcula la puntuación con fracciones exactas. **67 % o más aprueba la evaluación**; 66,5 % no se redondea para aprobar. Las respuestas y pesos originales se conservan como snapshots.

### Solicitudes y entrega

El listado administrativo permite filtrar evaluaciones aprobadas o no aprobadas. **Revisar** muestra identidad, respuestas originales, alertas y revisiones.

Una evaluación aprobada permite **Autorizar**, después de confirmar bienestar y registrar notas. Eso reserva la mascota y la marca **En proceso**. **Confirmar entrega definitiva** requiere autorización previa y registra una única entrega. Sólo entonces la mascota pasa a **Adoptada**.

**Rechazar** conserva el historial y, si había una autorización, libera la reserva. No se permite entregar dos veces ni cambiar manualmente una ficha para simular una adopción. Aprobar la encuesta no autoriza automáticamente la entrega.

## 14. Configuración

**Cuestionarios:** consulta criterios, preguntas, opciones y valores. Desde **Gestión de adopciones → Criterios y pesos** se crea una versión nueva; los pesos deben sumar exactamente 100. Puede publicarse o guardarse como borrador. **Editar pregunta** cambia texto, respuestas, valores y alertas del borrador. Las versiones activas o ya utilizadas se protegen contra edición.

**Cuentas del equipo:** visible sólo para superusuarios. Permite crear cuentas y editar nombre, correo, contraseña y permisos. Una contraseña vacía durante la edición conserva la actual; una contraseña nueva revoca las sesiones de esa cuenta. No se permite quitarse los propios permisos administrativos.

**Antecedentes conservados:** consulta la implementación histórica de adopción sin recalcular sus puntuaciones con el cuestionario actual. La limpieza de demostración deja estos historiales vacíos.

## 15. Datos de demostración y limpieza autorizada

La carga siguiente describe la demostración opcional anterior. La última operación solicitada utiliza `scripts/limpiar_datos.py --aplicar`: vacía datos operativos, verifica un respaldo y conserva los superusuarios sin volver a cargar ejemplos. `docs/evidencias/limpieza-base.json` contiene los conteos posteriores.

La preparación conserva **todos los campos y hashes de los superusuarios**, sus relaciones de permisos, la configuración del cuestionario y los metadatos necesarios del esquema. Elimina las cuentas no superusuarias y los datos operativos anteriores. No borra tablas, no recrea MySQL y no modifica la configuración privada de Gmail/MySQL.

| Datos | Cantidad inicial |
|---|---:|
| Clientes | 5 |
| Mascotas clínicas | 9 |
| Veterinarios / empleados | 5 / 5 |
| Citas | 5 |
| Facturas / líneas | 5 / 10 |
| Vacunas | 5 |
| Tratamientos | 5 |
| Mascotas disponibles para adopción | 5 |
| Solicitudes de adopción de ejemplo | 5 |
| Notificaciones de demostración, sin envío real | 5 |

| Cliente ficticio | Mascotas |
|---|---|
| Laura Martínez | Luna y Simón |
| Carlos Gómez | Rocky |
| Ana Torres | Mía, Bruno y Kiara |
| Diego Ramírez | Toby |
| Sofía Castro | Nina y Leo |

Los profesionales ficticios son Valentina Rojas, Andrés Herrera, Camila Mendoza, Sebastián López y Daniela Morales. El catálogo incluye Nala, Max, Mila, Coco y Olivia, todas disponibles. Tres solicitudes de ejemplo aprueban la evaluación y dos no; ninguna se entrega automáticamente.

Los correos terminan en `.invalid` y los teléfonos/documentos indican demostración. Para probar correo real, editar conscientemente el cliente con una dirección propia y registrar o modificar una cita. La muestra no utiliza automáticamente la dirección privada del administrador.

Los identificadores no se renumeran: se dejan avanzar los contadores de MySQL. La operación valida conteos, relaciones, facturas y conservación de superusuarios antes de confirmar la transacción. Ante un fallo se revierte la limpieza y la carga.

### Volver a preparar la demostración

La carga **nunca se ejecuta al abrir el programa**. Es una operación administrativa destructiva y explícita. Primero detener el servidor y el worker para evitar escrituras concurrentes. El comando sin opciones sólo previsualiza los conteos:

```powershell
.\.venv-wsgi\Scripts\python.exe scripts/preparar_demostracion.py
```

Para reemplazar deliberadamente los datos operativos por los ejemplos, conservando superusuarios:

```powershell
.\.venv-wsgi\Scripts\python.exe scripts/preparar_demostracion.py --aplicar
```

Antes de modificar filas se crea y verifica una copia SQL privada en `.codex/backups/vetcare`, fuera del proyecto. Contiene datos sensibles y no forma parte de GitHub ni del ZIP compartido. Las tablas técnicas y los archivos de fotografías se conservan; no se elimina recursivamente ningún directorio.

## 16. Qué ocurre al pulsar Guardar

`HTML → JavaScript/fetch → API Python → validación → transacción SQL → JSON → actualización de la vista`.

JavaScript desactiva los botones mientras envía el formulario, adjunta la cookie de sesión, el token CSRF y la clave de idempotencia. Python comprueba permisos y campos otra vez. El cambio y su respuesta se guardan en una misma transacción. Si se repite una clave con los mismos datos, devuelve el resultado anterior; si cambian los datos, se rechaza con 409.

Los listados usan paginación y consultas con JOIN; los importes se calculan con Decimal. Las solicitudes SQL reciben los valores como parámetros, y las rutas de archivos se resuelven dentro de sus directorios permitidos. PDF, SMTP y fotografías tienen servicios independientes.

## 17. Funciones de JavaScript

| Archivo | Funciones y responsabilidad |
|---|---|
| `frontend/assets/js/bootstrap.js` | Obtiene la sesión, prepara CSRF y nombre del usuario, carga los scripts adecuados, gestiona el login y presenta el resultado privado. `load()` carga los scripts en orden. |
| `frontend/assets/js/owner-search.js` | `bindOwnerSearch()` conecta el desplegable reutilizable; `search()` consulta propietarios, `highlight()` mueve la selección de teclado, `choose()` aplica el propietario y `hide()` cierra la lista. `ownerSearchCleanup()` cancela eventos, respuestas antiguas y temporizadores al navegar. |
| `js/clinic.js`: comunicación | `api()` procesa HTTP/JSON y errores; `toast()` muestra avisos; `bindForm()` asocia el elemento del formulario a su endpoint mediante WeakMap. El listener de submit genera/reutiliza la clave de operación y bloquea botones. Los elementos retirados pueden liberarse sin conservar manejadores por sus identificadores. |
| `js/clinic.js`: presentación | `esc`, `cop`, `badge`, `today`, `field`, `select`, `area`, `title`, `table`, `submit`, `openModal` escapan texto, formatean importes y construyen controles, tablas y ventanas. |
| `js/clinic.js`: familias | `ownerFields`, `petFields`, `renumberPets`, `addPet`, `registrar`, `consultar`, `addExistingPet`, `editPet` organizan propietarios, fichas dinámicas y edición. |
| `js/clinic.js`: agenda | `appointmentRows`, `bindCitaButtons`, `dashboard`, `citas`, `showCita`, `appointmentForm` presentan citas y conectan búsqueda de propietario, selector de mascotas y guardado. La ayuda interna `chooseOwner()` carga los pacientes del propietario elegido. |
| `js/clinic.js`: clínica y finanzas | `veterinarios`, `vacunacion`, `loadHealth`, `reportes`, `addService`, `updateTotal`, `newInvoice`, `showInvoice`, `correos` implementan los módulos respectivos. `navigate()` cambia de sección y descarta respuestas antiguas al navegar rápido. |
| `js/clinic.js`: ayudas internas | Las funciones `load()` de citas/consulta y `loadInvoices()` solicitan las páginas y aplican sus filtros; `rows()` vuelve a construir las líneas de servicios y sus totales; `edit()` prepara el alta o edición del veterinario. |
| `js/clinic.js`: pagos | `paymentMethodField()` construye el mismo selector de Transferencia/Efectivo/Tarjeta para alta y actualización. |
| `js/adoptions-admin.js` | `adoptionAdmin()` carga fichas y solicitudes; sus funciones internas paginan ambos listados. `editAdoptionPet()`, `adoptionPhoto()`, `reviewApplication()` y `editWeights()` registran fichas, fotos, revisiones y versiones. |
| `js/adoptions-public.js` | `initialize()` abre la mascota indicada en la URL; `load()` filtra/pagina el catálogo; `start()` construye el cuestionario; `show()` y `valid()` controlan pasos y campos. `request()`, `message()`, `input()` y `escapeText()` gestionan peticiones, avisos y controles seguros. |
| `js/configuration.js` | `editOwner()`, `configuration()`, `historicalAdoptions()`, `editAccount()`, `viewVersion()` y `editQuestion()` implementan gestión de propietarios, cuentas, versiones y antecedentes. |
| `js/interface.js` | Contrae el menú y anima indicadores, respetando la preferencia de movimiento reducido. |

## 18. Referencia de funciones Python

El siguiente inventario incluye las funciones de la aplicación, sus métodos, ayudas internas y comandos. Las pruebas automatizadas están en `tests/` y los recorridos de navegador en `tests/browser/prueba_*.cjs`; no son funciones clínicas que deban ejecutarse en la base operativa.

<!-- INICIO-INVENTARIO-PYTHON -->
Funciones documentadas: **166**.

### vetcare/application.py

| Función | Qué hace |
|---|---|
| `Application.__init__(self, config=None)` | Crea el pool, el mapa de rutas y el tratamiento del proxy según el entorno. |
| `Application.__call__(self, environ, start_response)` | Expone la aplicación como callable WSGI para Waitress o Gunicorn. |
| `Application.add(self, method, path, fn, admin=False, write=False)` | Registra método, ruta, función y controles administrativos/de escritura. |
| `Application.dispatch(self, environ, start_response)` | Valida host, HTTPS, sesión, permisos y CSRF; invoca el servicio y genera una respuesta segura. |
| `Application.mutate(self, ctx, fn, args)` | Confirma operación, respuesta e idempotencia en una transacción; resuelve reenvíos y colisiones de clave. |
| `Application.asset(self, ctx, path)` | Sirve un recurso público, negocia gzip en producción y conserva ETag/304 por variante. |
| `Application.html(self, ctx, name)` | Sirve una página HTML estática. |
| `Application.dashboard_html(self, ctx)` | Protege el dashboard y redirige al acceso cuando falta autenticación. |
| `Application.session(self, ctx)` | Devuelve los datos mínimos del usuario para preparar la interfaz. |
| `Application.photo(self, ctx, pet_id)` | Lee una foto de adopción mediante una ruta restringida y cacheable. |
| `Application.upload(self, ctx, pet_id)` | Valida tamaño/dimensiones, elimina metadatos y guarda una fotografía WebP con nombre aleatorio. |
| `Application.invoice_pdf(self, ctx, invoice_id)` | Entrega el PDF de una factura como descarga. |
| `Application.own_html(self, ctx, code)` | Comprueba la propiedad de una solicitud antes de mostrar el resultado. |
| `Application.ready(self, ctx)` | Comprueba que el servicio puede consultar MySQL. |
| `Application.login_html(self, ctx)` | Evita pedir acceso otra vez cuando el administrador ya tiene una sesión válida. |
| `Application.register_routes(self)` | Asocia todos los endpoints, alias, permisos e idempotencia. |
| `create_app(config=None)` | Construye una instancia aislada de la aplicación con su configuración. |

### vetcare/config.py

| Función | Qué hace |
|---|---|
| `session_run_id()` | Obtiene una identidad común por ejecución o despliegue para las sesiones autenticadas. |
| `Config.load(cls, database=None, testing=False)` | Carga .env sin revelar secretos, valida MySQL/firma/volumen y limita las bases utilizadas por pruebas. |
| `Config.hosts(self)` | Calcula los hosts permitidos, incluido el dominio público configurado. |

### vetcare/db.py

| Función | Qué hace |
|---|---|
| `Database.__init__(self, config)` | Prepara los slots del pool de conexiones por proceso. |
| `Database.connect(self, database=True, multi=False)` | Abre una conexión PyMySQL con tiempos límite, charset y aislamiento READ COMMITTED. |
| `Database.lease(self)` | Presta una conexión, comprueba conexiones antiguas y descarta sockets cerrados al devolverla. |
| `Database.close(self)` | Cierra las conexiones disponibles del pool. |
| `SQL.__init__(self, connection)` | Envuelve una conexión y comienza su contador de consultas. |
| `SQL.all(self, statement, params=())` | Ejecuta una consulta parametrizada y devuelve sus filas como diccionarios. |
| `SQL.one(self, statement, params=())` | Devuelve la primera fila o None. |
| `SQL.execute(self, statement, params=())` | Ejecuta una sentencia parametrizada y devuelve el identificador insertado. |
| `SQL.many(self, statement, rows)` | Ejecuta un lote parametrizado para evitar inserciones individuales innecesarias. |
| `SQL.atomic(self)` | Inicia una transacción y decide COMMIT o ROLLBACK según el resultado. |
| `insert(db, table, values)` | Construye INSERT con identificadores internos y parámetros para todos los valores. |
| `update(db, table, values, pk, pk_name='id')` | Actualiza campos internos de una fila identificada por su clave primaria. |

### vetcare/demo.py

| Función | Qué hace |
|---|---|
| `table_counts(db)` | Obtiene conteos sin exponer nombres, correos u otros datos de personas. |
| `clear_operational_data(db)` | Valida tablas conocidas, limpia hijos/relaciones operativas y conserva superusuarios y configuración. |
| `save_demo_application(ctx, pet_id, index, questionnaire, base_date)` | Calcula y guarda respuestas y puntuación de una solicitud ficticia con el motor real. |
| `prepare_demo(db, base_date)` | Carga el conjunto completo dentro de una transacción y verifica conteos, relaciones y conservación de cuentas. |

### vetcare/http.py

| Función | Qué hace |
|---|---|
| `json_default(value)` | Convierte Decimal y fechas/horas en valores JSON estables. |
| `response_json(value, status=200)` | Crea una respuesta JSON UTF-8 y su código HTTP. |
| `Context.__init__(self, app, environ)` | Prepara petición, límites de carga, sesión, cookies y gestión de recursos. |
| `Context.db(self)` | Reserva la conexión sólo cuando la petición realmente necesita SQL. |
| `Context.data(self)` | Acepta un objeto JSON o campos de formulario y rechaza otras estructuras. |
| `Context.finish(self, response)` | Añade cookies de sesión/CSRF o las elimina al cerrar sesión. |
| `page(query, params, ctx, key, serialize=lambda row: row, size=50, always=False)` | Pagina con LIMIT tamaño+1 y publica el indicador de página siguiente. |

### vetcare/maintenance.py

| Función | Qué hace |
|---|---|
| `encode(value)` | Convierte valores especiales para un respaldo lógico JSON. |
| `snapshot(database, backup=False)` | Captura esquema/filas de forma consistente y verifica el respaldo privado, o genera conteos y hashes sin filas. |

### vetcare/migrations.py

| Función | Qué hace |
|---|---|
| `migrate(database)` | Aplica SQL versionado con lock de esquema y checksum; no repite archivos ya aplicados. |
| `schema_inventory(db)` | Consulta columnas, tipos y claves de la base activa. |

### vetcare/security.py

| Función | Qué hace |
|---|---|
| `digest(value)` | Calcula SHA-256 para tokens, claves de control y propietarios de sesiones. |
| `verify_password(password, stored)` | Verifica hashes Argon2 y formatos heredados sin almacenar contraseñas en claro. |
| `ensure_session(ctx)` | Recupera una sesión vigente y, para usuarios, comprueba la identidad de ejecución; si falta crea una anónima. |
| `legacy_owner(ctx)` | Reconoce de forma verificada al propietario de una solicitud procedente de una sesión antigua. |
| `decode_legacy(value, secret)` | Verifica la firma de una sesión heredada antes de interpretar su JSON limitado. |
| `new_session(ctx, user_id=None, owner_hash=None)` | Genera tokens aleatorios, guarda sus hashes y vincula el acceso autenticado a la ejecución actual. |
| `user(ctx)` | Obtiene únicamente identidad y permisos de una cuenta activa. |
| `admin(ctx)` | Exige usuario activo con permiso staff antes de entrar a una API administrativa. |
| `csrf(ctx)` | Comprueba el token de formulario y el origen de una escritura. |
| `login(ctx)` | Limita intentos, valida credenciales, actualiza el hash cuando corresponde y rota la sesión. |
| `logout(ctx)` | Revoca la sesión actual y ordena borrar sus cookies. |

### vetcare/services/accounts.py

| Función | Qué hace |
|---|---|
| `authorize(ctx)` | Exige superusuario para administrar cuentas. |
| `list_users(ctx)` | Lista identidades y permisos sin devolver hashes ni contraseñas. |
| `save(ctx, user_id=None)` | Crea/actualiza cuentas, protege permisos propios y revoca sesiones al cambiar una contraseña. |

### vetcare/services/adoptions.py

| Función | Qué hace |
|---|---|
| `load_json(value)` | Interpreta JSON guardado por MySQL cuando el driver lo devuelve como texto. |
| `pet_data(p, private=False)` | Publica la ficha permitida de adopción; el vínculo clínico se incluye sólo para administración. |
| `catalog(ctx, private=False)` | Filtra y pagina las mascotas del catálogo o de administración. |
| `public_pet(ctx, pet_id)` | Devuelve la ficha pública de una mascota disponible para abrir su encuesta directamente. |
| `questionnaire(ctx, qid=None)` | Obtiene una versión y agrupa criterios, preguntas y opciones desde SQL. |
| `schema(ctx)` | Publica preguntas/opciones sin divulgar los valores de puntuación al visitante. |
| `evaluate(q, answers)` | Comprueba respuestas completas, calcula fracciones exactas y obtiene puntuación, alertas y snapshots. |
| `public_result(s)` | Muestra porcentaje sin redondear para aprobar, estado y recomendaciones sin datos personales. |
| `application_values(d)` | Valida mayoría de edad, consentimiento, contacto y condiciones declaradas por el solicitante. |
| `apply(ctx, pet_id)` | Valida la mascota disponible, la versión y la clave de operación; guarda solicitud y respuestas atomícamente. |
| `apply.replay(previous)` | Devuelve un envío previo únicamente al propietario de esa sesión y con la misma huella. |
| `own_result(ctx, code)` | Comprueba el propietario de sesión antes de devolver un resultado privado. |
| `save_pet(ctx)` | Crea o edita una ficha, preservando estados controlados por la revisión/entrega. |
| `applicant_data(s)` | Prepara datos administrativos del solicitante y su evaluación. |
| `applications(ctx)` | Filtra y pagina solicitudes por evaluación aprobada/no aprobada. |
| `detail(ctx, application_id)` | Devuelve solicitud, respuestas originales e historial de revisiones para el equipo autorizado. |
| `review(ctx, application_id)` | Bloquea mascota/solicitud y registra autorización, rechazo o entrega, comprobando bienestar y unicidad. |
| `clone_questionnaire(ctx)` | Crea una nueva versión con los pesos solicitados sin modificar resultados anteriores. |
| `edit_draft(ctx, qid)` | Edita pregunta y opciones sólo en una versión no activa y sin solicitudes. |
| `publish(ctx, qid)` | Valida el borrador, desactiva la versión anterior y publica la seleccionada. |

### vetcare/services/billing.py

| Función | Qué hace |
|---|---|
| `summary(ctx)` | Agrega cantidad de facturas e importes por estado de pago. |
| `list_invoices(ctx)` | Filtra y pagina el historial de facturas. |
| `list_invoices.serialize(f)` | Selecciona los campos del listado y su enlace de descarga. |
| `get_invoice(ctx, invoice_id)` | Obtiene factura, propietario, cita, paciente y servicios con importes calculados. |
| `detail(ctx, invoice_id)` | Prepara el detalle JSON utilizado por la ventana de factura. |
| `save(ctx)` | Valida servicios y pertenencia, calcula Decimal y guarda cabecera/líneas con el administrador de la sesión. |
| `change_state(ctx)` | Valida y actualiza el estado de pago. |
| `options(ctx)` | Carga citas no canceladas para seleccionar cliente/paciente al facturar. |

### vetcare/services/clinic.py

| Función | Qué hace |
|---|---|
| `NOW()` | Obtiene fecha/hora de la clínica en America/Bogota. |
| `appointment_order()` | Comparte el orden de fecha/hora de agenda, resumen y selectores: hoy y futuras primero; después el historial, del más reciente al más antiguo. |
| `pet_data(m)` | Serializa una mascota con propietario y datos de contacto para las vistas administrativas. |
| `owner(c)` | Serializa los campos de un cliente. |
| `time_value(value)` | Normaliza el TIME de MySQL a una hora Python. |
| `appointment(c)` | Serializa una cita y compara su final, incluyendo la duración, con la hora de Colombia. |
| `complete_finished_appointments(db, now=None)` | Marca Atendida al alcanzar fecha, hora y duración de citas programadas; conserva cancelaciones y no envía correo. |
| `dashboard(ctx)` | Consulta indicadores y citas pendientes sin consultas por cada fila. |
| `customers(ctx, customer_id=None)` | Busca propietarios o consulta uno por identificador. |
| `pets(ctx, customer_id=None)` | Busca/pagina pacientes o devuelve las mascotas de un cliente concreto. |
| `customer_values(d, new=False)` | Valida y selecciona sólo campos permitidos del propietario. |
| `pet_values(d)` | Valida y selecciona sólo campos permitidos del paciente. |
| `register_family(ctx)` | Guarda un propietario y entre una y 50 mascotas en lote. |
| `add_pet(ctx, customer_id)` | Añade un paciente a un propietario existente. |
| `pet_detail(ctx, pet_id)` | Devuelve la ficha conjunta del paciente y su propietario. |
| `edit_record(ctx)` | Edita paciente/propietario comprobando su pertenencia y conserva estados no modificados explícitamente. |
| `delete_pet(ctx, pet_id)` | Elimina únicamente un paciente sin historial protegido. |
| `edit_customer(ctx, customer_id)` | Edita sólo los datos del propietario. |
| `delete_customer(ctx, customer_id)` | Elimina un propietario cuando no tiene mascotas ni facturas y sus FK lo permiten. |
| `vets(ctx)` | Lista profesionales con los datos de empleado relacionados. |
| `save_vet(ctx)` | Crea o modifica empleado y veterinario sin duplicar la identidad profesional. |
| `delete_vet(ctx, vet_id)` | Retira un profesional sin citas ni otras relaciones protegidas. |
| `appointment_list(ctx, pet_id=None, pending=False)` | Consulta/pagina citas, pendientes o citas de un paciente. |
| `appointment_detail(ctx, appointment_id)` | Consulta cita y estados de notificación. |
| `save_appointment(ctx, appointment_id=None)` | Valida propietario/paciente, bloquea profesionales, impide solapamientos y guarda cita/notificación. |
| `vaccines(ctx, pet_id)` | Consulta vacunas del paciente y días hasta vencer. |
| `save_vaccine(ctx)` | Valida las fechas y guarda una vacuna para un paciente existente. |
| `treatments(ctx, pet_id)` | Consulta tratamientos unidos a las citas del paciente. |
| `save_treatment(ctx)` | Valida y registra un tratamiento vinculado a una cita. |

### vetcare/services/history.py

| Función | Qué hace |
|---|---|
| `adoptions(ctx)` | Pagina antecedentes del esquema anterior sin recalcular sus resultados. |
| `detail(ctx, adoption_id)` | Obtiene el registro histórico y sus evaluaciones originales. |

### vetcare/services/mail.py

| Función | Qué hace |
|---|---|
| `notification_state(recipient)` | Distingue destinatarios reales, sin correo y direcciones reservadas de demostración. |
| `smtp_settings()` | Valida host, puerto, transporte, credenciales y remitente sin mostrar sus valores privados. |
| `smtp_connection()` | Abre SMTP con TLS/SSL y autentica cuando corresponde; cierra la conexión al terminar. |
| `check_smtp_connection()` | Comprueba SMTP y autenticación mediante NOOP, sin enviar mensajes. |
| `mail_error(exc)` | Traduce errores conocidos a diagnósticos seguros sin respuestas privadas del proveedor. |
| `list_messages(ctx)` | Consulta estados e intentos de las notificaciones recientes. |
| `retry(ctx, message_id)` | Devuelve una notificación fallida a Pendiente para un nuevo intento. |
| `make_message(n)` | Construye el mensaje MIME con texto y HTML escapado a partir del contexto guardado. |
| `smtp_send(message)` | Entrega el mensaje al servidor SMTP y detecta destinatarios rechazados. |
| `deliver_one(database, sender=smtp_send)` | Reclama una notificación con SKIP LOCKED, envía fuera de la transacción y guarda aceptación o fallo. |

### vetcare/services/pdf.py

| Función | Qué hace |
|---|---|
| `cop(value)` | Formatea un importe como moneda COP para el documento. |
| `build(f, root)` | Genera el PDF con ReportLab, detalle real, totales y marca de gestión interna. |
| `build.p(value, style='BodyText')` | Escapa texto y lo convierte en un párrafo del documento. |
| `build.footer(canvas, document)` | Dibuja pie de página y numeración en cada hoja. |

### vetcare/services/scheduler.py

| Función | Qué hace |
|---|---|
| `start_monitor(database, interval=15)` | Inicia el monitor de agenda cada 15 segundos, independiente del correo. |
| `start_monitor.run()` | Actualiza citas finalizadas y registra fallos sin secretos; continúa tras errores temporales. |
| `stop_monitor(monitor)` | Señala la detención del monitor al cerrar el servidor y espera su finalización. |

### vetcare/validation.py

| Función | Qué hace |
|---|---|
| `Problem.__init__(self, message, status=400)` | Representa un error previsto con mensaje seguro y estado HTTP. |
| `required(row, name, max_length=200, optional=False)` | Valida presencia y longitud de un campo. |
| `integer(value, name='valor', minimum=0, maximum=2147483647)` | Valida un entero exacto y su rango, excluyendo booleanos. |
| `money(value, maximum='99999999.99')` | Valida un Decimal finito no negativo con hasta dos decimales. |
| `day(value, name='fecha')` | Interpreta una fecha ISO válida. |
| `clock(value)` | Interpreta una hora local sin zona horaria incrustada. |
| `email(value, optional=False)` | Valida la estructura básica y longitud de un correo. |
| `choice(value, allowed, name='estado')` | Restringe un valor a las opciones admitidas por el servicio. |
| `found(row)` | Convierte la ausencia de un registro en una respuesta 404. |

### run.py

| Función | Qué hace |
|---|---|
| `seed(database)` | Siembra el cuestionario inicial sólo cuando no existe ninguno. |
| `main()` | Ejecuta serve, check, migrate, worker, create-admin, backup o integrity según el comando. |

### gunicorn.conf.py

| Función | Qué hace |
|---|---|
| `post_worker_init(worker)` | Activa el monitor de citas con el pool del proceso de Gunicorn recién iniciado. |
| `worker_exit(server, worker)` | Detiene el monitor de agenda al finalizar ese proceso. |

### scripts/build_assets.py

| Función | Qué hace |
|---|---|
| `build_assets(root=ROOT)` | Genera recursos CSS/JS gzip reproducibles y un manifiesto de tamaños y hashes, sin leer secretos. |

### scripts/comprobar_integridad_wsgi.py

| Función | Qué hace |
|---|---|
| `compare(path)` | Compara filas con un respaldo privado y guarda únicamente el resultado de integridad. |
| `compare.sort(records)` | Ordena registros serializados para comparar respaldos sin depender del orden físico. |

### scripts/configurar_gmail.py

| Función | Qué hace |
|---|---|
| `gmail_values(address, password)` | Valida dirección y clave de aplicación y prepara los parámetros Gmail. |
| `save_configuration(path, values)` | Actualiza únicamente las claves SMTP del .env privado. |
| `main(argv=None)` | Solicita datos ocultos, comprueba acceso SMTP sin enviar y guarda sólo tras éxito. |

### scripts/documentar_funciones.py

| Función | Qué hace |
|---|---|
| `definitions(nodes, prefix='')` | Recorre funciones, métodos y ayudas anidadas del AST para construir nombres completos. |
| `main()` | Verifica que cada función tenga descripción y actualiza este inventario dentro del Markdown. |

### scripts/empaquetar_wsgi.py

| Función | Qué hace |
|---|---|
| `private_patterns(root=ROOT)` | Lee valores privados sólo para detectar su presencia accidental en archivos, sin imprimirlos. |
| `create_archive(target, web=False, root=ROOT)` | Construye y verifica un ZIP de fuente con exclusiones de secretos, entornos y archivos generados. |
| `main()` | Genera un paquete web ligero y otro completo con las evidencias de pruebas. |

### scripts/limpiar_datos.py

| Función | Qué hace |
|---|---|
| `main(argv=None)` | Previsualiza o respalda/vacía datos operativos en una transacción, preservando superusuarios sin cargar ejemplos. |

### scripts/preparar_demostracion.py

| Función | Qué hace |
|---|---|
| `main(argv=None)` | Previsualiza o respalda/aplica la limpieza y genera su informe de conteos. |

### scripts/verificar_despliegue.py

| Función | Qué hace |
|---|---|
| `check_source(root=ROOT)` | Valida las referencias estáticas, Railway y la copia selectiva del Dockerfile. |
| `check_database()` | Comprueba MySQL y los checksums aplicados mediante consultas de sólo lectura. |
| `main(argv=None)` | Ejecuta la revisión estática y, opcionalmente, la comprobación de base sin publicar ni modificar datos. |
<!-- FIN-INVENTARIO-PYTHON -->
