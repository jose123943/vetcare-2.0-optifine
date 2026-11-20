# Estructura del proyecto explicada de forma sencilla

VetCare es un sistema para gestionar una veterinaria. La interfaz recoge los datos; el servidor comprueba permisos y reglas; MySQL conserva la información. Este mapa explica cada archivo de código en una frase.

## Por dónde empezar

1. [README.md](../README.md): instalar y ejecutar el programa.
2. [run.py](../run.py): encontrar los comandos de arranque y mantenimiento.
3. [vetcare/application.py](../vetcare/application.py): seguir las peticiones de la web.
4. [vetcare/services/](../vetcare/services/): consultar las reglas de cada módulo.
5. [vetcare-funciones.md](../vetcare-funciones.md): entender las pestañas y las funciones.

## Qué contiene cada carpeta

| Carpeta | Para qué sirve |
|---|---|
| `vetcare/` | Código Python que recibe peticiones, protege el acceso y aplica las reglas. |
| `vetcare/services/` | Gestión de clínica, cuentas, adopciones, facturas, PDF y correo. |
| `frontend/pages/` | Las cuatro pantallas HTML: acceso, administración, catálogo y resultado. |
| `frontend/assets/` | JavaScript, estilos e imágenes utilizados por las pantallas. |
| `scripts/` | Configuración, respaldo, limpieza, pruebas y preparación de paquetes. |
| `sql/` | Cambios versionados de estructura de la base de datos. |
| `tests/` | Comprobaciones automáticas con datos ficticios. |
| `docs/` | Guías del proyecto e informes de comprobaciones anteriores. |

## Arranque, instalación y publicación

| Archivo | Para qué sirve |
|---|---|
| [run.py](../run.py) | Permite iniciar VetCare y ejecutar sus tareas de revisión, respaldo y mantenimiento. |
| [gunicorn.conf.py](../gunicorn.conf.py) | Configura el servidor Linux que publica VetCare y mantiene el monitor de citas. |
| [iniciar.ps1](../iniciar.ps1) | Inicia la web local o el proceso de correo usando el entorno Python del proyecto. |
| [instalar.ps1](../instalar.ps1) | Prepara el entorno Python, instala dependencias y comprueba la configuración local. |
| [Dockerfile](../Dockerfile) | Prepara la imagen de ejecución de VetCare para publicarla en un servidor. |
| [Procfile](../Procfile) | Indica cómo iniciar el servidor web y el consumidor independiente de correos. |
| [.github/workflows/verificar.yml](../.github/workflows/verificar.yml) | Comprueba el código y la construcción de la imagen al actualizar GitHub. |
| [.gitignore](../.gitignore) | Indica qué archivos privados, temporales o generados deben quedar fuera de Git. |
| [.dockerignore](../.dockerignore) | Excluye secretos, archivos de desarrollo y datos privados de la construcción Docker. |
| [.gitattributes](../.gitattributes) | Conserva correctamente los archivos de texto, binarios y migraciones al clonar. |
| [.editorconfig](../.editorconfig) | Unifica el formato del código y protege los bytes de los SQL ya aplicados. |
| [requirements.txt](../requirements.txt) | Lista las bibliotecas necesarias para ejecutar VetCare. |
| [requirements-dev.txt](../requirements-dev.txt) | Añade las bibliotecas utilizadas para comprobar el proyecto durante el desarrollo. |

## Backend: lo que hace el servidor

| Archivo | Para qué sirve |
|---|---|
| [vetcare/__init__.py](../vetcare/__init__.py) | Identifica el paquete que contiene el backend de VetCare. |
| [vetcare/application.py](../vetcare/application.py) | Recibe las peticiones de la web, revisa permisos y las dirige al servicio adecuado. |
| [vetcare/config.py](../vetcare/config.py) | Carga y valida la configuración privada antes de iniciar la aplicación. |
| [vetcare/db.py](../vetcare/db.py) | Reutiliza conexiones MySQL y permite guardar cambios completos o revertirlos si fallan. |
| [vetcare/default_questions.py](../vetcare/default_questions.py) | Define las preguntas y los puntos de la encuesta inicial de adopción. |
| [vetcare/demo.py](../vetcare/demo.py) | Prepara datos ficticios o limpia datos operativos cuando se solicita expresamente. |
| [vetcare/http.py](../vetcare/http.py) | Prepara los datos de cada petición y las respuestas JSON que utiliza la interfaz. |
| [vetcare/maintenance.py](../vetcare/maintenance.py) | Crea respaldos privados y comprueba la integridad de los datos. |
| [vetcare/migrations.py](../vetcare/migrations.py) | Aplica cambios pendientes de estructura SQL y comprueba los ya registrados. |
| [vetcare/security.py](../vetcare/security.py) | Controla el acceso, las contraseñas, las sesiones y los permisos de cada usuario. |
| [vetcare/validation.py](../vetcare/validation.py) | Comprueba que los datos recibidos tengan el formato y los valores permitidos. |
| [vetcare/wsgi.py](../vetcare/wsgi.py) | Entrega la aplicación al servidor que la ejecuta en la nube. |
| [vetcare/services/__init__.py](../vetcare/services/__init__.py) | Agrupa las reglas de negocio de la clínica, las adopciones y el correo. |
| [vetcare/services/accounts.py](../vetcare/services/accounts.py) | Administra las cuentas del equipo y revoca sesiones cuando cambian sus permisos. |
| [vetcare/services/adoptions.py](../vetcare/services/adoptions.py) | Gestiona mascotas para adoptar, encuestas, evaluaciones, autorizaciones y entregas. |
| [vetcare/services/billing.py](../vetcare/services/billing.py) | Calcula y guarda facturas, sus servicios y los estados de pago. |
| [vetcare/services/clinic.py](../vetcare/services/clinic.py) | Gestiona propietarios, pacientes, veterinarios, citas, vacunas y tratamientos. |
| [vetcare/services/history.py](../vetcare/services/history.py) | Permite consultar los antecedentes de adopción conservados de versiones anteriores. |
| [vetcare/services/mail.py](../vetcare/services/mail.py) | Guarda el estado de las notificaciones y envía los mensajes por correo. |
| [vetcare/services/pdf.py](../vetcare/services/pdf.py) | Construye una factura PDF a partir de los datos y los importes guardados. |
| [vetcare/services/scheduler.py](../vetcare/services/scheduler.py) | Marca como atendidas las citas que ya terminaron, usando la hora de Colombia. |

## Interfaz: lo que ve y utiliza la persona

| Archivo | Para qué sirve |
|---|---|
| [frontend/assets/js/bootstrap.js](../frontend/assets/js/bootstrap.js) | Prepara la sesión y carga los módulos JavaScript que necesita cada pantalla. |
| [frontend/assets/js/clinic.js](../frontend/assets/js/clinic.js) | Conecta las pestañas de la clínica con sus formularios, listados y notificaciones. |
| [frontend/assets/js/configuration.js](../frontend/assets/js/configuration.js) | Permite administrar propietarios, cuentas del equipo y versiones de la encuesta. |
| [frontend/assets/js/interface.js](../frontend/assets/js/interface.js) | Controla el menú y las animaciones visuales del dashboard. |
| [frontend/assets/js/owner-search.js](../frontend/assets/js/owner-search.js) | Comparte el buscador de propietarios entre la consulta de pacientes y la agenda. |
| [frontend/assets/js/adoptions-admin.js](../frontend/assets/js/adoptions-admin.js) | Permite al equipo gestionar mascotas en adopción, solicitudes y entregas. |
| [frontend/assets/js/adoptions-public.js](../frontend/assets/js/adoptions-public.js) | Muestra el catálogo público y guía al visitante por la encuesta de adopción. |
| [frontend/assets/css/app.css](../frontend/assets/css/app.css) | Define los colores, formularios, tablas y distribución básica de la aplicación. |
| [frontend/assets/css/interface.css](../frontend/assets/css/interface.css) | Ajusta el menú, los buscadores y las animaciones a distintas pantallas. |
| [frontend/assets/css/adoptions.css](../frontend/assets/css/adoptions.css) | Da estilo al catálogo, la encuesta y los resultados de adopción. |
| [frontend/pages/login.html](../frontend/pages/login.html) | Pantalla donde el personal introduce su usuario y contraseña. |
| [frontend/pages/dashboard.html](../frontend/pages/dashboard.html) | Pantalla principal que reúne las pestañas de gestión de la veterinaria. |
| [frontend/pages/catalog.html](../frontend/pages/catalog.html) | Pantalla pública para conocer mascotas y solicitar una adopción. |
| [frontend/pages/result.html](../frontend/pages/result.html) | Pantalla privada donde el solicitante consulta su evaluación de adopción. |

## Herramientas de configuración y mantenimiento

| Archivo | Para qué sirve |
|---|---|
| [scripts/build_assets.py](../scripts/build_assets.py) | Genera copias comprimidas de CSS y JavaScript para cargar la web más rápido. |
| [scripts/comprobar_integridad_wsgi.py](../scripts/comprobar_integridad_wsgi.py) | Compara la base de datos con un respaldo privado sin publicar sus registros. |
| [scripts/configurar_gmail.py](../scripts/configurar_gmail.py) | Solicita y comprueba las credenciales de Gmail antes de guardarlas localmente. |
| [scripts/configurar_wsgi.py](../scripts/configurar_wsgi.py) | Crea el archivo privado de conexión local si todavía no existe. |
| [scripts/documentar_funciones.py](../scripts/documentar_funciones.py) | Actualiza el inventario de funciones Python de la guía vetcare-funciones.md. |
| [scripts/empaquetar_wsgi.py](../scripts/empaquetar_wsgi.py) | Crea paquetes ZIP del proyecto y comprueba que no incluyan secretos. |
| [scripts/limpiar_datos.py](../scripts/limpiar_datos.py) | Muestra qué datos se limpiarían; solo --aplicar respalda y ejecuta la limpieza. |
| [scripts/preparar_demostracion.py](../scripts/preparar_demostracion.py) | Previsualiza los ejemplos; solo --aplicar respalda y carga la demostración. |
| [scripts/probar_wsgi.py](../scripts/probar_wsgi.py) | Ejecuta las pruebas en bases aisladas y guarda un resumen de sus resultados. |
| [scripts/verificar_despliegue.py](../scripts/verificar_despliegue.py) | Revisa los archivos de publicación; --con-base también comprueba MySQL. |

## Pruebas: cómo se comprueba el funcionamiento

| Archivo | Para qué sirve |
|---|---|
| [tests/__init__.py](../tests/__init__.py) | Identifica el paquete que reúne las pruebas del proyecto. |
| [tests/support.py](../tests/support.py) | Prepara aplicaciones, cuentas y datos ficticios para probar sin alterar la base operativa. |
| [tests/linux_smoke.py](../tests/linux_smoke.py) | Comprueba que la web arranque con Gunicorn en Linux usando una base de pruebas. |
| [tests/test_agenda_payment.py](../tests/test_agenda_payment.py) | Comprueba la agenda, los buscadores, los pagos y la limpieza con datos aislados. |
| [tests/test_demo_sessions.py](../tests/test_demo_sessions.py) | Comprueba las sesiones, la encuesta directa y la preparación segura de ejemplos. |
| [tests/test_deployment.py](../tests/test_deployment.py) | Comprueba la configuración de publicación y los archivos públicos sin conectar a MySQL. |
| [tests/test_gmail.py](../tests/test_gmail.py) | Comprueba la configuración de Gmail sin enviar mensajes a destinatarios reales. |
| [tests/test_smtp.py](../tests/test_smtp.py) | Comprueba el envío de un correo a un receptor local que simula un servidor SMTP. |
| [tests/test_wsgi.py](../tests/test_wsgi.py) | Comprueba los módulos de VetCare mediante peticiones HTTP y una base de pruebas. |
| [tests/browser/preparar_wsgi_navegador.py](../tests/browser/preparar_wsgi_navegador.py) | Prepara datos y una sesión temporal para los recorridos de navegador. |
| [tests/browser/servidor_pruebas_wsgi.py](../tests/browser/servidor_pruebas_wsgi.py) | Abre un servidor local conectado exclusivamente a una base de pruebas. |
| [tests/browser/prueba_adopciones.cjs](../tests/browser/prueba_adopciones.cjs) | Recorre el catálogo, la encuesta y la entrega de una adopción en el navegador de pruebas. |
| [tests/browser/prueba_agenda_propietarios.cjs](../tests/browser/prueba_agenda_propietarios.cjs) | Comprueba buscadores, citas y medios de pago en el navegador de pruebas. |
| [tests/browser/prueba_configuracion.cjs](../tests/browser/prueba_configuracion.cjs) | Comprueba cuentas, cuestionarios y vacunas desde el navegador de pruebas. |
| [tests/browser/prueba_crud.cjs](../tests/browser/prueba_crud.cjs) | Comprueba altas, cambios, eliminaciones protegidas y fotografías en el navegador de pruebas. |
| [tests/browser/prueba_demo_sesion_encuesta.cjs](../tests/browser/prueba_demo_sesion_encuesta.cjs) | Comprueba la sesión activa y la encuesta directa de una mascota con datos ficticios. |
| [tests/browser/prueba_navegador.cjs](../tests/browser/prueba_navegador.cjs) | Recorre el registro clínico, la agenda, la factura PDF y el cierre de sesión. |

## Datos y formatos que se explican fuera del archivo

Los JSON necesitan conservar su formato y los SQL aplicados tienen una huella de integridad. Sus explicaciones se mantienen aquí y en [la guía SQL](../sql/README.md).

| Archivo o grupo | Para qué sirve |
|---|---|
| [railway.json](../railway.json) | Indica cómo construir, arrancar y comprobar el servicio web en Railway. |
| [railway.worker.json](../railway.worker.json) | Indica cómo arrancar el consumidor independiente de correos en Railway. |
| [.env.example](../.env.example) | Plantilla con los nombres de configuración; las credenciales reales se introducen aparte. |
| `.env` | Configuración privada local de MySQL, firma de sesiones y correo; permanece fuera de Git. |
| [tests/fixtures/legacy.json](../tests/fixtures/legacy.json) | Datos ficticios para comprobar compatibilidad con contraseñas y sesiones antiguas. |
| [sql/000_esquema_existente.sql](../sql/000_esquema_existente.sql) | Define las tablas originales y sus relaciones. |
| [sql/001_wsgi.sql](../sql/001_wsgi.sql) | Añade la estructura necesaria para la aplicación WSGI. |
| [sql/002_sesion_programa.sql](../sql/002_sesion_programa.sql) | Relaciona la sesión autenticada con la ejecución del servidor. |
| `frontend/assets/images/` | Logotipo e ilustraciones que utilizan la interfaz y los PDF. |
| `docs/evidencias/` | Resultados históricos de pruebas, capturas y PDF ficticios. |

En los JSON de Railway, `build` describe la construcción y `deploy` el inicio y la comprobación del servicio. En las migraciones, las tablas de clínica relacionan propietario, paciente, cita y profesional; las de adopción conservan encuestas y entregas.

## Documentación y archivos generados

| Archivo o carpeta | Para qué sirve |
|---|---|
| [README.md](../README.md) | Instrucciones de instalación, ejecución y configuración del correo. |
| [vetcare-funciones.md](../vetcare-funciones.md) | Guía de uso de cada pestaña y referencia técnica de funciones. |
| [MIGRACION_WSGI.md](MIGRACION_WSGI.md) | Explica cómo se sustituyó Django conservando los módulos. |
| [RAILWAY.md](RAILWAY.md) | Preparación y configuración de un despliegue en Railway. |
| [PRUEBAS_WSGI.md](PRUEBAS_WSGI.md) | Resultados registrados y alcance de las comprobaciones. |
| [LIMPIEZA_PROYECTO.md](LIMPIEZA_PROYECTO.md) | Explica la limpieza realizada y las reglas de agenda y pagos. |
| [evidencias/README.md](evidencias/README.md) | Distingue informes históricos y respaldos privados. |
| [VetCare-historial-completo-de-cambios.pdf](VetCare-historial-completo-de-cambios.pdf) | Resume las correcciones y mejoras de las etapas documentadas de la conversación. |
| `.venv-wsgi/` | Entorno Python local con las bibliotecas instaladas. |
| `media/` | Fotografías guardadas por la aplicación; necesitan almacenamiento persistente en la nube. |
| `build/` | Recursos públicos comprimidos que se generan para producción. |
| `dist/` | Paquetes ZIP preparados para compartir o publicar el código. |

Los conteos de informes anteriores corresponden a su fecha de ejecución. Los respaldos con datos reales permanecen privados y separados de las evidencias compartidas.

## Ejemplo: qué ocurre al guardar una cita

1. El formulario de `clinic.js` recoge propietario, paciente, profesional y horario.
2. `application.py` comprueba la sesión y permite llegar al servicio de clínica.
3. `clinic.py` valida los datos y evita horarios incompatibles.
4. `db.py` confirma la cita y su notificación en MySQL.
5. La interfaz activa una petición separada para que `mail.py` procese el correo.

En [el apartado de Cloud Run del README](../README.md#correo-en-google-cloud-run) se explica la configuración de Gmail y el alcance del envío por HTTP. El consumidor independiente puede seguir ejecutándose con `run.py worker`.

## Palabras que aparecen en los comentarios

| Término | Significado sencillo |
|---|---|
| API / HTTP | Forma en que la pantalla pide datos o guarda cambios en el servidor. |
| JSON | Formato de los datos que intercambian JavaScript y Python. |
| WSGI | Conexión entre la aplicación Python y el servidor que atiende la web. |
| Transacción | Grupo de cambios que se confirma completo o se deshace si falla. |
| Pool | Conjunto de conexiones MySQL que se reutilizan en lugar de abrir una por consulta. |
| CSRF | Protección que comprueba que un envío procede de una sesión autorizada. |
| Idempotencia | Control para que repetir la misma operación no duplique registros. |
| Migración / checksum | Cambio versionado de estructura y huella que comprueba que su archivo no cambió. |
| SMTP | Protocolo utilizado para entregar notificaciones al proveedor de correo. |

Los comentarios de código explican el objetivo de una función o el motivo de un bloque. Se mantienen breves para que la explicación ayude a leer el código.
