import json
import os
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from html import escape

from ..db import update
from ..validation import Problem, found


def list_messages(ctx):
    return {
        "status": "ok",
        "notificaciones": ctx.db.all(
            "SELECT id,cita_id,estado,intentos,error,creada FROM pagInicio_notificacion ORDER BY id DESC LIMIT 100"
        ),
    }


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
    host = os.getenv("EMAIL_HOST")
    sender = os.getenv("DEFAULT_FROM_EMAIL")
    if not host or not sender:
        raise RuntimeError("SMTP no configurado")
    ssl = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
    tls = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    if ssl and tls:
        raise RuntimeError("No actives TLS y SSL a la vez")
    import ssl as ssl_module

    context = ssl_module.create_default_context()
    factory = smtplib.SMTP_SSL if ssl else smtplib.SMTP
    kwargs = {
        "host": host,
        "port": int(os.getenv("EMAIL_PORT", "465" if ssl else "587")),
        "timeout": 15,
    }
    if ssl:
        kwargs["context"] = context
    with factory(**kwargs) as server:
        if tls:
            server.starttls(context=context)
        if os.getenv("EMAIL_HOST_USER"):
            server.login(
                os.environ["EMAIL_HOST_USER"], os.getenv("EMAIL_HOST_PASSWORD", "")
            )
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
                {"estado": "Fallida", "error": type(exc).__name__[:250]},
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
