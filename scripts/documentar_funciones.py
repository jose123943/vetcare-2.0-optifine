# Actualiza el inventario de funciones Python de la guía vetcare-funciones.md.
"""Actualiza el inventario técnico de vetcare-funciones.md a partir del código."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Mantiene las explicaciones de las funciones que aparecerán en la guía técnica.
DESCRIPTIONS = {
    "application": {
        "Application.__init__": "Crea el pool, el mapa de rutas y el tratamiento del proxy según el entorno.",
        "Application.__call__": "Expone la aplicación como callable WSGI para Waitress o Gunicorn.",
        "Application.add": "Registra método, ruta, función y controles administrativos/de escritura.",
        "Application.dispatch": "Valida host, HTTPS, sesión, permisos y CSRF; invoca el servicio y genera una respuesta segura.",
        "Application.mutate": "Confirma operación, respuesta e idempotencia en una transacción; resuelve reenvíos y colisiones de clave.",
        "Application.asset": "Sirve un recurso público, negocia gzip en producción y conserva ETag/304 por variante.",
        "Application.html": "Sirve una página HTML estática.",
        "Application.dashboard_html": "Protege el dashboard y redirige al acceso cuando falta autenticación.",
        "Application.login_html": "Evita pedir acceso otra vez cuando el administrador ya tiene una sesión válida.",
        "Application.session": "Devuelve los datos mínimos del usuario para preparar la interfaz.",
        "Application.photo": "Lee una foto de adopción mediante una ruta restringida y cacheable.",
        "Application.upload": "Valida tamaño/dimensiones, elimina metadatos y guarda una fotografía WebP con nombre aleatorio.",
        "Application.invoice_pdf": "Entrega el PDF de una factura como descarga.",
        "Application.own_html": "Comprueba la propiedad de una solicitud antes de mostrar el resultado.",
        "Application.ready": "Comprueba que el servicio puede consultar MySQL.",
        "Application.register_routes": "Asocia todos los endpoints, alias, permisos e idempotencia.",
        "create_app": "Construye una instancia aislada de la aplicación con su configuración.",
    },
    "config": {
        "session_run_id": "Obtiene una identidad común por ejecución o despliegue para las sesiones autenticadas.",
        "Config.load": "Carga .env sin revelar secretos, valida MySQL/firma/volumen y limita las bases utilizadas por pruebas.",
        "Config.hosts": "Calcula los hosts permitidos, incluido el dominio público configurado.",
    },
    "db": {
        "Database.__init__": "Prepara los slots del pool de conexiones por proceso.",
        "Database.connect": "Abre una conexión PyMySQL con tiempos límite, charset y aislamiento READ COMMITTED.",
        "Database.lease": "Presta una conexión, comprueba conexiones antiguas y descarta sockets cerrados al devolverla.",
        "Database.close": "Cierra las conexiones disponibles del pool.",
        "SQL.__init__": "Envuelve una conexión y comienza su contador de consultas.",
        "SQL.all": "Ejecuta una consulta parametrizada y devuelve sus filas como diccionarios.",
        "SQL.one": "Devuelve la primera fila o None.",
        "SQL.execute": "Ejecuta una sentencia parametrizada y devuelve el identificador insertado.",
        "SQL.many": "Ejecuta un lote parametrizado para evitar inserciones individuales innecesarias.",
        "SQL.atomic": "Inicia una transacción y decide COMMIT o ROLLBACK según el resultado.",
        "insert": "Construye INSERT con identificadores internos y parámetros para todos los valores.",
        "update": "Actualiza campos internos de una fila identificada por su clave primaria.",
    },
    "http": {
        "json_default": "Convierte Decimal y fechas/horas en valores JSON estables.",
        "response_json": "Crea una respuesta JSON UTF-8 y su código HTTP.",
        "Context.__init__": "Prepara petición, límites de carga, sesión, cookies y gestión de recursos.",
        "Context.db": "Reserva la conexión sólo cuando la petición realmente necesita SQL.",
        "Context.data": "Acepta un objeto JSON o campos de formulario y rechaza otras estructuras.",
        "Context.finish": "Añade cookies de sesión/CSRF o las elimina al cerrar sesión.",
        "page": "Pagina con LIMIT tamaño+1 y publica el indicador de página siguiente.",
    },
    "security": {
        "digest": "Calcula SHA-256 para tokens, claves de control y propietarios de sesiones.",
        "verify_password": "Verifica hashes Argon2 y formatos heredados sin almacenar contraseñas en claro.",
        "ensure_session": "Recupera una sesión vigente y, para usuarios, comprueba la identidad de ejecución; si falta crea una anónima.",
        "legacy_owner": "Reconoce de forma verificada al propietario de una solicitud procedente de una sesión antigua.",
        "decode_legacy": "Verifica la firma de una sesión heredada antes de interpretar su JSON limitado.",
        "new_session": "Genera tokens aleatorios, guarda sus hashes y vincula el acceso autenticado a la ejecución actual.",
        "user": "Obtiene únicamente identidad y permisos de una cuenta activa.",
        "admin": "Exige usuario activo con permiso staff antes de entrar a una API administrativa.",
        "csrf": "Comprueba el token de formulario y el origen de una escritura.",
        "login": "Limita intentos, valida credenciales, actualiza el hash cuando corresponde y rota la sesión.",
        "logout": "Revoca la sesión actual y ordena borrar sus cookies.",
    },
    "validation": {
        "Problem.__init__": "Representa un error previsto con mensaje seguro y estado HTTP.",
        "required": "Valida presencia y longitud de un campo.",
        "integer": "Valida un entero exacto y su rango, excluyendo booleanos.",
        "money": "Valida un Decimal finito no negativo con hasta dos decimales.",
        "day": "Interpreta una fecha ISO válida.",
        "clock": "Interpreta una hora local sin zona horaria incrustada.",
        "email": "Valida la estructura básica y longitud de un correo.",
        "choice": "Restringe un valor a las opciones admitidas por el servicio.",
        "found": "Convierte la ausencia de un registro en una respuesta 404.",
    },
    "migrations": {
        "migrate": "Aplica SQL versionado con lock de esquema y checksum; no repite archivos ya aplicados.",
        "schema_inventory": "Consulta columnas, tipos y claves de la base activa.",
    },
    "maintenance": {
        "encode": "Convierte valores especiales para un respaldo lógico JSON.",
        "snapshot": "Captura esquema/filas de forma consistente y verifica el respaldo privado, o genera conteos y hashes sin filas.",
    },
    "demo": {
        "table_counts": "Obtiene conteos sin exponer nombres, correos u otros datos de personas.",
        "clear_operational_data": "Valida tablas conocidas, limpia hijos/relaciones operativas y conserva superusuarios y configuración.",
        "save_demo_application": "Calcula y guarda respuestas y puntuación de una solicitud ficticia con el motor real.",
        "prepare_demo": "Carga el conjunto completo dentro de una transacción y verifica conteos, relaciones y conservación de cuentas.",
    },
    "clinic": {
        "NOW": "Obtiene fecha/hora de la clínica en America/Bogota.",
        "appointment_order": "Ordena primero las citas de hoy y futuras; después muestra el historial desde la más reciente.",
        "pet_data": "Serializa una mascota con propietario y datos de contacto para las vistas administrativas.",
        "owner": "Serializa los campos de un cliente.",
        "time_value": "Normaliza el TIME de MySQL a una hora Python.",
        "appointment": "Serializa una cita y compara su final, incluyendo la duración, con la hora de Colombia.",
        "complete_finished_appointments": "Marca Atendida al alcanzar fecha, hora y duración de citas programadas; conserva cancelaciones y no envía correo.",
        "dashboard": "Consulta indicadores y citas pendientes sin consultas por cada fila.",
        "customers": "Busca propietarios o consulta uno por identificador.",
        "pets": "Busca/pagina pacientes o devuelve las mascotas de un cliente concreto.",
        "customer_values": "Valida y selecciona sólo campos permitidos del propietario.",
        "pet_values": "Valida y selecciona sólo campos permitidos del paciente.",
        "register_family": "Guarda un propietario y entre una y 50 mascotas en lote.",
        "add_pet": "Añade un paciente a un propietario existente.",
        "pet_detail": "Devuelve la ficha conjunta del paciente y su propietario.",
        "edit_record": "Edita paciente/propietario comprobando su pertenencia y conserva estados no modificados explícitamente.",
        "delete_pet": "Elimina únicamente un paciente sin historial protegido.",
        "edit_customer": "Edita sólo los datos del propietario.",
        "delete_customer": "Elimina un propietario cuando no tiene mascotas ni facturas y sus FK lo permiten.",
        "vets": "Lista profesionales con los datos de empleado relacionados.",
        "save_vet": "Crea o modifica empleado y veterinario sin duplicar la identidad profesional.",
        "delete_vet": "Retira un profesional sin citas ni otras relaciones protegidas.",
        "appointment_list": "Consulta/pagina citas, pendientes o citas de un paciente.",
        "appointment_detail": "Consulta cita y estados de notificación.",
        "save_appointment": "Valida propietario/paciente, bloquea profesionales, impide solapamientos y guarda cita/notificación.",
        "vaccines": "Consulta vacunas del paciente y días hasta vencer.",
        "save_vaccine": "Valida las fechas y guarda una vacuna para un paciente existente.",
        "treatments": "Consulta tratamientos unidos a las citas del paciente.",
        "save_treatment": "Valida y registra un tratamiento vinculado a una cita.",
    },
    "billing": {
        "summary": "Agrega cantidad de facturas e importes por estado de pago.",
        "list_invoices": "Filtra y pagina el historial de facturas.",
        "list_invoices.serialize": "Selecciona los campos del listado y su enlace de descarga.",
        "get_invoice": "Obtiene factura, propietario, cita, paciente y servicios con importes calculados.",
        "detail": "Prepara el detalle JSON utilizado por la ventana de factura.",
        "save": "Valida servicios y pertenencia, calcula Decimal y guarda cabecera/líneas con el administrador de la sesión.",
        "change_state": "Valida y actualiza el estado de pago.",
        "options": "Carga citas no canceladas para seleccionar cliente/paciente al facturar.",
    },
    "scheduler": {
        "start_monitor": "Inicia el monitor de agenda cada 15 segundos, independiente del correo.",
        "start_monitor.run": "Actualiza citas finalizadas y registra fallos sin secretos; continúa tras errores temporales.",
        "stop_monitor": "Señala la detención del monitor al cerrar el servidor y espera su finalización.",
    },
    "gunicorn.conf": {
        "post_worker_init": "Activa el monitor de citas con el pool del proceso de Gunicorn recién iniciado.",
        "worker_exit": "Detiene el monitor de agenda al finalizar ese proceso.",
    },
    "adoptions": {
        "load_json": "Interpreta JSON guardado por MySQL cuando el driver lo devuelve como texto.",
        "pet_data": "Publica la ficha permitida de adopción; el vínculo clínico se incluye sólo para administración.",
        "catalog": "Filtra y pagina las mascotas del catálogo o de administración.",
        "public_pet": "Devuelve la ficha pública de una mascota disponible para abrir su encuesta directamente.",
        "questionnaire": "Obtiene una versión y agrupa criterios, preguntas y opciones desde SQL.",
        "schema": "Publica preguntas/opciones sin divulgar los valores de puntuación al visitante.",
        "evaluate": "Comprueba respuestas completas, calcula fracciones exactas y obtiene puntuación, alertas y snapshots.",
        "public_result": "Muestra porcentaje sin redondear para aprobar, estado y recomendaciones sin datos personales.",
        "application_values": "Valida mayoría de edad, consentimiento, contacto y condiciones declaradas por el solicitante.",
        "apply": "Valida la mascota disponible, la versión y la clave de operación; guarda solicitud y respuestas atomícamente.",
        "apply.replay": "Devuelve un envío previo únicamente al propietario de esa sesión y con la misma huella.",
        "own_result": "Comprueba el propietario de sesión antes de devolver un resultado privado.",
        "save_pet": "Crea o edita una ficha, preservando estados controlados por la revisión/entrega.",
        "applicant_data": "Prepara datos administrativos del solicitante y su evaluación.",
        "applications": "Filtra y pagina solicitudes por evaluación aprobada/no aprobada.",
        "detail": "Devuelve solicitud, respuestas originales e historial de revisiones para el equipo autorizado.",
        "review": "Bloquea mascota/solicitud y registra autorización, rechazo o entrega, comprobando bienestar y unicidad.",
        "clone_questionnaire": "Crea una nueva versión con los pesos solicitados sin modificar resultados anteriores.",
        "edit_draft": "Edita pregunta y opciones sólo en una versión no activa y sin solicitudes.",
        "publish": "Valida el borrador, desactiva la versión anterior y publica la seleccionada.",
    },
    "accounts": {
        "authorize": "Exige superusuario para administrar cuentas.",
        "list_users": "Lista identidades y permisos sin devolver hashes ni contraseñas.",
        "save": "Crea/actualiza cuentas, protege permisos propios y revoca sesiones al cambiar una contraseña.",
    },
    "history": {
        "adoptions": "Pagina antecedentes del esquema anterior sin recalcular sus resultados.",
        "detail": "Obtiene el registro histórico y sus evaluaciones originales.",
    },
    "mail": {
        "notification_state": "Distingue destinatarios reales, sin correo y direcciones reservadas de demostración.",
        "smtp_settings": "Valida host, puerto, transporte, credenciales y remitente sin mostrar sus valores privados.",
        "smtp_connection": "Abre SMTP con TLS/SSL y autentica cuando corresponde; cierra la conexión al terminar.",
        "check_smtp_connection": "Comprueba SMTP y autenticación mediante NOOP, sin enviar mensajes.",
        "mail_error": "Traduce errores conocidos a diagnósticos seguros sin respuestas privadas del proveedor.",
        "configuration_status": "Explica qué configuración de correo falta sin revelar sus valores privados.",
        "list_messages": "Consulta estados e intentos de las notificaciones recientes.",
        "process_pending": "Procesa un correo pendiente dentro de una petición web autorizada.",
        "retry": "Devuelve una notificación fallida a Pendiente para un nuevo intento.",
        "make_message": "Construye el mensaje MIME con texto y HTML escapado a partir del contexto guardado.",
        "smtp_send": "Entrega el mensaje al servidor SMTP y detecta destinatarios rechazados.",
        "claim_message": "Reserva un mensaje pendiente para que otro proceso no lo envíe al mismo tiempo.",
        "deliver_one": "Reclama una notificación con SKIP LOCKED, envía fuera de la transacción y guarda aceptación o fallo.",
    },
    "pdf": {
        "cop": "Formatea un importe como moneda COP para el documento.",
        "build": "Genera el PDF con ReportLab, detalle real, totales y marca de gestión interna.",
        "build.p": "Escapa texto y lo convierte en un párrafo del documento.",
        "build.footer": "Dibuja pie de página y numeración en cada hoja.",
    },
    "run": {
        "seed": "Siembra el cuestionario inicial sólo cuando no existe ninguno.",
        "main": "Ejecuta serve, check, migrate, worker, create-admin, backup o integrity según el comando.",
    },
    "configurar_gmail": {
        "gmail_values": "Valida dirección y clave de aplicación y prepara los parámetros Gmail.",
        "save_configuration": "Actualiza únicamente las claves SMTP del .env privado.",
        "main": "Solicita datos ocultos, comprueba acceso SMTP sin enviar y guarda sólo tras éxito.",
    },
    "preparar_demostracion": {
        "main": "Previsualiza o respalda/aplica la limpieza y genera su informe de conteos.",
    },
    "limpiar_datos": {
        "main": "Previsualiza o respalda/vacía datos operativos en una transacción, preservando superusuarios sin cargar ejemplos.",
    },
    "comprobar_integridad_wsgi": {
        "compare": "Compara filas con un respaldo privado y guarda únicamente el resultado de integridad.",
        "compare.sort": "Ordena registros serializados para comparar respaldos sin depender del orden físico.",
    },
    "build_assets": {
        "build_assets": "Genera recursos CSS/JS gzip reproducibles y un manifiesto de tamaños y hashes, sin leer secretos.",
    },
    "verificar_despliegue": {
        "check_source": "Valida las referencias estáticas, Railway y la copia selectiva del Dockerfile.",
        "check_database": "Comprueba MySQL y los checksums aplicados mediante consultas de sólo lectura.",
        "main": "Ejecuta la revisión estática y, opcionalmente, la comprobación de base sin publicar ni modificar datos.",
    },
    "empaquetar_wsgi": {
        "private_patterns": "Lee valores privados sólo para detectar su presencia accidental en archivos, sin imprimirlos.",
        "create_archive": "Construye y verifica un ZIP de fuente con exclusiones de secretos, entornos y archivos generados.",
        "main": "Genera un paquete web ligero y otro completo con las evidencias de pruebas.",
    },
    "documentar_funciones": {
        "definitions": "Recorre funciones, métodos y ayudas anidadas del AST para construir nombres completos.",
        "main": "Verifica que cada función tenga descripción y actualiza este inventario dentro del Markdown.",
    },
}


# Recorre funciones, métodos y ayudas anidadas del AST para construir nombres completos.
def definitions(nodes, prefix=""):
    for node in nodes:
        if isinstance(node, ast.ClassDef):
            yield from definitions(node.body, prefix + node.name + ".")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield prefix + node.name, node
            yield from definitions(node.body, prefix + node.name + ".")
        else:
            yield from definitions(list(ast.iter_child_nodes(node)), prefix)


# Verifica que cada función tenga descripción y actualiza este inventario dentro del Markdown.
def main():
    files = (
        sorted((ROOT / "vetcare").rglob("*.py"))
        + [ROOT / "run.py", ROOT / "gunicorn.conf.py"]
        + sorted((ROOT / "scripts").glob("*.py"))
    )
    sections = []
    number = 0
    for path in files:
        functions = list(definitions(ast.parse(path.read_text(encoding="utf-8")).body))
        if not functions:
            continue
        mapping = DESCRIPTIONS.get(path.stem, {})
        missing = [name for name, _ in functions if name not in mapping]
        if missing:
            raise RuntimeError(
                "Falta documentar "
                + str(path.relative_to(ROOT))
                + ": "
                + ", ".join(missing)
            )
        sections += [
            "\n### " + path.relative_to(ROOT).as_posix() + "\n",
            "| Función | Qué hace |",
            "|---|---|",
        ]
        sections += [
            f"| `{name}({ast.unparse(node.args)})` | {mapping[name]} |"
            for name, node in functions
        ]
        number += len(functions)
    text = (ROOT / "vetcare-funciones.md").read_text(encoding="utf-8")
    begin = "<!-- INICIO-INVENTARIO-PYTHON -->"
    end = "<!-- FIN-INVENTARIO-PYTHON -->"
    before, rest = text.split(begin, 1)
    _, after = rest.split(end, 1)
    (ROOT / "vetcare-funciones.md").write_text(
        before
        + begin
        + "\n"
        + f"Funciones documentadas: **{number}**.\n"
        + "\n".join(sections)
        + "\n"
        + end
        + after,
        encoding="utf-8",
    )
    print("Funciones Python documentadas:", number)


if __name__ == "__main__":
    main()
