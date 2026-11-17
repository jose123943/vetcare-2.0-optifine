"""Asistente privado para Gmail: comprueba SMTP sin enviar correos."""

import argparse
import getpass
import os
import re
import sys
from email.utils import formataddr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv, set_key
from vetcare.config import ROOT
from vetcare.services.mail import (
    MailConfigurationError,
    check_smtp_connection,
    mail_error,
)
from vetcare.validation import Problem, email


def gmail_values(address, password):
    address = email(address)
    password = "".join(password.split())
    if not re.fullmatch(r"[A-Za-z0-9]{16}", password):
        raise MailConfigurationError(
            "La contraseña de aplicación debe tener 16 caracteres. Copia la clave completa de Google; no escribas asteriscos."
        )
    return {
        "EMAIL_HOST": "smtp.gmail.com",
        "EMAIL_PORT": "587",
        "EMAIL_USE_TLS": "true",
        "EMAIL_USE_SSL": "false",
        "EMAIL_HOST_USER": address,
        "EMAIL_HOST_PASSWORD": password,
        "DEFAULT_FROM_EMAIL": formataddr(("VetCare", address)),
    }


def save_configuration(path, values):
    if not path.is_file():
        raise MailConfigurationError(
            "Primero configura MySQL con scripts/configurar_wsgi.py; falta .env."
        )
    for key, value in values.items():
        set_key(path, key, value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comprobar",
        action="store_true",
        help="Comprobar la configuración guardada, sin enviar mensajes.",
    )
    args = parser.parse_args(argv)
    path = ROOT / ".env"
    load_dotenv(path, override=False, interpolate=False)
    if args.comprobar:
        check_smtp_connection()
        print("Gmail aceptó la conexión y la autenticación. No se envió ningún correo.")
        return 0
    if not path.is_file():
        raise MailConfigurationError(
            "Falta .env. Ejecuta primero scripts/configurar_wsgi.py."
        )
    if not sys.stdin.isatty():
        raise MailConfigurationError(
            "Ejecuta este asistente directamente en la terminal de VS Code para introducir la clave de forma oculta."
        )
    print("Usa una contraseña de aplicación de Google (16 caracteres).")
    print("Crear clave: https://myaccount.google.com/apppasswords")
    values = gmail_values(
        input("Dirección Gmail remitente: ").strip(),
        getpass.getpass("Contraseña de aplicación (entrada oculta): "),
    )
    os.environ.update(values)
    print("Comprobando TLS y autenticación con Gmail, sin enviar mensajes…", flush=True)
    check_smtp_connection()
    save_configuration(path, values)
    print("Configuración validada y guardada en .env privado.")
    print("Reinicia el worker: .\\.venv-wsgi\\Scripts\\python.exe run.py worker")
    print(
        "Después pulsa Reintentar en la notificación fallida y Actualizar para consultar su estado."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nConfiguración cancelada.")
        raise SystemExit(1)
    except Problem as exc:
        print(exc.message, file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(mail_error(exc), file=sys.stderr)
        raise SystemExit(1)
