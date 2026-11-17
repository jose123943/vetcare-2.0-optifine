import json
import os
import smtplib
import socket
import ssl
from contextlib import contextmanager
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import parseaddr
from html import escape

from ..db import update
from ..validation import Problem, found


class MailConfigurationError(RuntimeError):
    """Mensaje controlado sin valores privados de la configuración."""


def notification_state(recipient):
    """Las direcciones reservadas de demostración nunca se ponen en envío real."""
    if not recipient:
        return "Sin correo"
    if recipient.rsplit("@", 1)[-1].lower().endswith(".invalid"):
        return "Demostración"
    return "Pendiente"


def smtp_settings():
    host = os.getenv("EMAIL_HOST", "").strip()
    sender = os.getenv("DEFAULT_FROM_EMAIL", "").strip()
    missing = [
        name
        for name, value in [("EMAIL_HOST", host), ("DEFAULT_FROM_EMAIL", sender)]
        if not value
    ]
    if missing:
        raise MailConfigurationError(
            "Configura "
            + ", ".join(missing)
            + " en .env. Para Gmail: python scripts/configurar_gmail.py."
        )
    use_ssl = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
    use_tls = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    if use_ssl and use_tls:
        raise MailConfigurationError("Activa solo uno: EMAIL_USE_TLS o EMAIL_USE_SSL.")
    try:
        port = int(os.getenv("EMAIL_PORT", "465" if use_ssl else "587"))
        if not 1 <= port <= 65535:
            raise ValueError()
    except ValueError:
        raise MailConfigurationError(
            "EMAIL_PORT debe ser un puerto numérico válido."
        ) from None
    username = os.getenv("EMAIL_HOST_USER", "").strip()
    password = os.getenv("EMAIL_HOST_PASSWORD", "")
    if host.lower() == "smtp.gmail.com":
        if not username or not password:
            raise MailConfigurationError(
                "Gmail requiere EMAIL_HOST_USER y EMAIL_HOST_PASSWORD (contraseña de aplicación). Ejecuta python scripts/configurar_gmail.py."
            )
        if not (
            (port == 587 and use_tls and not use_ssl)
            or (port == 465 and use_ssl and not use_tls)
        ):
            raise MailConfigurationError(
                "Gmail requiere puerto 587 con TLS, o 465 con SSL."
            )
        password = "".join(password.split())
        if len(password) != 16:
            raise MailConfigurationError(
                "Introduce la contraseña de aplicación completa de Google: 16 caracteres, sin espacios."
            )
        if parseaddr(sender)[1].casefold() != username.casefold():
            raise MailConfigurationError(
                "Para esta configuración de Gmail, DEFAULT_FROM_EMAIL debe usar la misma dirección que EMAIL_HOST_USER."
            )
    elif bool(username) != bool(password):
        raise MailConfigurationError(
            "Completa EMAIL_HOST_USER y EMAIL_HOST_PASSWORD juntos."
        )
    return dict(
        host=host,
        port=port,
        sender=sender,
        username=username,
        password=password,
        use_ssl=use_ssl,
        use_tls=use_tls,
    )


@contextmanager
def smtp_connection():
    settings = smtp_settings()
    context = ssl.create_default_context()
    factory = smtplib.SMTP_SSL if settings["use_ssl"] else smtplib.SMTP
    kwargs = dict(host=settings["host"], port=settings["port"], timeout=15)
    if settings["use_ssl"]:
        kwargs["context"] = context
    with factory(**kwargs) as server:
        if settings["use_tls"]:
            server.starttls(context=context)
        if settings["username"]:
            server.login(settings["username"], settings["password"])
        yield server


def check_smtp_connection():
    """Comprueba conexión/autenticación sin enviar mensajes ni tocar la cola."""
    with smtp_connection() as server:
        code, _ = server.noop()
        if not 200 <= code < 300:
            raise smtplib.SMTPException("Verificación SMTP rechazada")


def mail_error(exc):
    """Diagnóstico visible que nunca incorpora respuestas o credenciales del proveedor."""
    if isinstance(exc, MailConfigurationError):
        return str(exc)[:250]
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "El servidor rechazó el acceso. En Gmail utiliza una contraseña de aplicación vigente y activa la verificación en dos pasos."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "El servidor rechazó el destinatario. Revisa el correo del cliente de la cita."
    if isinstance(exc, ssl.SSLCertVerificationError):
        return "No se pudo verificar el certificado TLS del servidor de correo. Revisa la red y la fecha del equipo."
    if isinstance(
        exc,
        (
            TimeoutError,
            ConnectionError,
            socket.gaierror,
            smtplib.SMTPServerDisconnected,
        ),
    ):
        return "No se pudo conectar con el servidor de correo. Revisa Internet, el host y el puerto SMTP."
    if isinstance(exc, smtplib.SMTPResponseException):
        return f"El proveedor rechazó el envío (SMTP {exc.smtp_code}). Revisa la cuenta y sus límites de envío."
    return type(exc).__name__[:250]


def list_messages(ctx):
    rows = ctx.db.all(
        "SELECT id,cita_id,estado,intentos,error,creada FROM pagInicio_notificacion ORDER BY id DESC LIMIT 100"
    )
    for row in rows:
        if row["error"] == "RuntimeError":
            row["error"] = (
                "Revisa la configuración SMTP y reinicia el proceso de correo antes de reintentar."
            )
    return {"status": "ok", "notificaciones": rows}


def retry(ctx, message_id):
    row = found(
        ctx.db.one(
            "SELECT estado FROM pagInicio_notificacion WHERE id=%s FOR UPDATE",
            (message_id,),
        )
    )
    if row["estado"] != "Fallida":
        raise Problem(
            "Solo se pueden reintentar mensajes fallidos tras revisar la configuración."
        )
    update(
        ctx.db,
        "pagInicio_notificacion",
        {"estado": "Pendiente", "error": ""},
        message_id,
    )
    return {"status": "ok", "message": "Notificación en cola de nuevo."}


def make_message(n):
    context = (
        json.loads(n["contexto"]) if isinstance(n["contexto"], str) else n["contexto"]
    )
    message = EmailMessage()
    message["Subject"] = n["asunto"]
    message["From"] = os.getenv("DEFAULT_FROM_EMAIL", "")
    message["To"] = n["destinatario"]
    message["Message-ID"] = f"<vetcare-{n['id']}@notifications.vetcare>"
    text = f"Hola {context['cliente']}, tu cita para {context['mascota']} es el {context['fecha']} a las {context['hora']}. Veterinario: {context['veterinario']}. Motivo: {context['motivo']}. Estado: {context['estado']}."
    message.set_content(text)
    rows = "".join(
        f'<tr><th align="left" style="padding:10px">{label}</th><td>{escape(str(context[key]))}</td></tr>'
        for key, label in [
            ("mascota", "Mascota"),
            ("veterinario", "Veterinario"),
            ("fecha", "Fecha"),
            ("hora", "Hora"),
            ("motivo", "Motivo"),
            ("estado", "Estado"),
        ]
    )
    message.add_alternative(
        '<!doctype html><html lang="es"><body style="background:#edf5f3;font-family:Arial;padding:30px"><main style="background:white;border-top:6px solid #14836e;padding:30px;max-width:560px;margin:auto"><h1 style="color:#14836e">VetCare</h1><p>Hola, '
        + escape(context["cliente"])
        + ". Estos son los datos de tu cita:</p><table>"
        + rows
        + "</table><p>Si la cita sigue activa, llega unos minutos antes. ¡Gracias por confiar en nosotros!</p><p>Equipo VetCare</p></main></body></html>",
        subtype="html",
    )
    return message


def smtp_send(message):
    with smtp_connection() as server:
        refused = server.send_message(message)
        if refused:
            raise RuntimeError("Destinatario rechazado")


def deliver_one(database, sender=smtp_send):
    with database.lease() as db:
        with db.atomic():
            n = db.one(
                "SELECT * FROM pagInicio_notificacion WHERE estado='Pendiente' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
            )
            if not n:
                return False
            db.execute(
                "UPDATE pagInicio_notificacion SET estado='Enviando',intentos=intentos+1 WHERE id=%s",
                (n["id"],),
            )
    try:
        sender(make_message(n))
    except Exception as exc:
        with database.lease() as db:
            update(
                db,
                "pagInicio_notificacion",
                {"estado": "Fallida", "error": mail_error(exc)},
                n["id"],
            )
    else:
        with database.lease() as db:
            update(
                db,
                "pagInicio_notificacion",
                {
                    "estado": "Enviada",
                    "enviada": datetime.now(UTC).replace(tzinfo=None),
                    "error": "",
                },
                n["id"],
            )
    return True
