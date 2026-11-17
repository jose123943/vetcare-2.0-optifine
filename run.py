"""Comandos independientes del framework anterior. Nunca imprimen credenciales."""

import argparse
import getpass
import logging
import os
import sys
import time
from datetime import UTC, datetime

from vetcare.config import Config
from vetcare.db import Database, insert


def seed(database):
    from vetcare.default_questions import DEFAULTS

    with database.lease() as db, db.atomic():
        if db.one("SELECT id FROM adopciones_cuestionario LIMIT 1"):
            return
        qid = insert(
            db,
            "adopciones_cuestionario",
            dict(
                nombre="VetCare · Evaluación responsable v1",
                activa=True,
                creada=datetime.now(UTC).replace(tzinfo=None),
            ),
        )
        for order, (name, weight, recommendation, questions) in enumerate(DEFAULTS):
            cid = insert(
                db,
                "adopciones_criterio",
                dict(
                    cuestionario_id=qid,
                    nombre=name,
                    peso=weight,
                    recomendacion=recommendation,
                    orden=order,
                ),
            )
            for position, (text, options) in enumerate(questions):
                pid = insert(
                    db,
                    "adopciones_pregunta",
                    dict(criterio_id=cid, texto=text, orden=position),
                )
                db.many(
                    "INSERT INTO adopciones_opcion(pregunta_id,texto,valor,alerta,orden) VALUES (%s,%s,%s,%s,%s)",
                    [
                        (pid, o[0], o[1], o[2] if len(o) > 2 else "", i)
                        for i, o in enumerate(options)
                    ],
                )


def main():
    parser = argparse.ArgumentParser(description="VetCare · Python WSGI + MySQL")
    parser.add_argument(
        "command",
        choices=[
            "serve",
            "check",
            "migrate",
            "worker",
            "create-admin",
            "backup",
            "integrity",
        ],
    )
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--test-db", help="Solo base de pruebas aislada test_vetcare_")
    args = parser.parse_args()
    config = Config.load(database=args.test_db, testing=bool(args.test_db))
    database = Database(config)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    if args.command == "serve":
        from waitress import serve

        from vetcare.application import create_app

        print(
            f"VetCare disponible en http://{args.host}:{args.port} (Waitress, sin Django)",
            flush=True,
        )
        serve(
            create_app(config),
            host=args.host,
            port=args.port,
            threads=config.pool_size,
            clear_untrusted_proxy_headers=True,
        )
    elif args.command == "migrate":
        from vetcare.migrations import migrate

        migrate(database)
        seed(database)
        print("Migraciones SQL aditivas verificadas. Datos existentes conservados.")
    elif args.command == "worker":
        from vetcare.services.mail import deliver_one, smtp_settings

        smtp_settings()
        print("Worker de notificaciones iniciado.", flush=True)
        while True:
            try:
                if not deliver_one(database):
                    time.sleep(3)
            except Exception as exc:
                logging.error("Worker: %s", type(exc).__name__)
                time.sleep(5)
    elif args.command == "create-admin":
        from vetcare.security import hasher

        username = input("Usuario nuevo: ").strip()
        password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
        if (
            not username
            or len(username) > 150
            or len(password) < 12
            or len(password) > 1024
        ):
            raise ValueError("Usuario o contraseña no válidos.")
        if password != getpass.getpass("Repite la contraseña: "):
            raise ValueError("Las contraseñas no coinciden.")
        with database.lease() as db, db.atomic():
            insert(
                db,
                "auth_user",
                dict(
                    username=username,
                    password=hasher.hash(password),
                    email="",
                    first_name="",
                    last_name="",
                    is_active=True,
                    is_staff=True,
                    is_superuser=True,
                    last_login=None,
                    date_joined=datetime.now(UTC).replace(tzinfo=None),
                ),
            )
        print("Cuenta nueva creada. Las cuentas anteriores no se modifican.")
    elif args.command in ("backup", "integrity"):
        from vetcare.maintenance import snapshot

        snapshot(database, backup=args.command == "backup")
    else:
        import importlib.util

        from vetcare.migrations import schema_inventory

        with database.lease() as db:
            db.one("SELECT 1 AS ok")
            tables = {r["TABLE_NAME"] for r in schema_inventory(db)}
            missing = {
                "cliente",
                "mascota",
                "cita",
                "factura",
                "auth_user",
                "vc_session",
                "vc_session_scope",
                "vc_login_bucket",
            } - tables
            if missing:
                raise RuntimeError(
                    "Faltan tablas; ejecuta python run.py migrate: "
                    + ", ".join(sorted(missing))
                )
        print(
            "Conexión MySQL exitosa. Esquema disponible. Django instalado:",
            importlib.util.find_spec("django") is not None,
        )
    database.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else ""
        print(
            f"Error {type(exc).__name__} {code}. Revisa .env y la configuración; no se muestran secretos.",
            file=sys.stderr,
        )
        if code == 1045:
            print(
                "Corrige MYSQLPASSWORD con la contraseña vigente de MySQL → Database → Config → Connection en Railway. Usa el host y puerto públicos de Connect para Windows.",
                file=sys.stderr,
            )
        elif isinstance(exc, (ValueError, RuntimeError)):
            print(str(exc), file=sys.stderr)
        sys.exit(1)
