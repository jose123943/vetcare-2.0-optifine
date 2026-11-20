# Muestra qué datos se limpiarían; solo --aplicar respalda y ejecuta la limpieza.
"""Vacía datos operativos con respaldo, conservando superusuarios y configuración."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vetcare.config import Config
from vetcare.db import Database
from vetcare.demo import OPERATIONAL_TABLES, clear_operational_data, table_counts
from vetcare.maintenance import snapshot


# Previsualiza o respalda/vacía datos operativos en una transacción, preservando superusuarios sin cargar ejemplos.
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar", action="store_true", help="Confirma el vaciado; no carga ejemplos."
    )
    parser.add_argument("--test-db", help="Sólo bases aisladas test_vetcare_.")
    args = parser.parse_args(argv)
    config = Config.load(database=args.test_db, testing=bool(args.test_db))
    database = Database(config)
    try:
        if not args.aplicar:
            with database.lease() as db:
                print(
                    json.dumps(
                        {
                            "accion": "Previsualización; no se modificó nada",
                            "conteos": table_counts(db),
                        },
                        indent=2,
                    )
                )
            return
        snapshot(database, backup=True)
        with database.lease() as db:
            lock = "vetcare-demo-" + config.database
            if db.one("SELECT GET_LOCK(%s,0) AS n", (lock,))["n"] != 1:
                raise RuntimeError("Otra limpieza o carga está en curso.")
            try:
                with db.atomic():
                    supers = clear_operational_data(db)
                    counts = table_counts(db)
                    if any(counts[table] for table in OPERATIONAL_TABLES):
                        raise RuntimeError("Quedaron datos operativos; se revierte.")
                    if (
                        db.all(
                            "SELECT * FROM auth_user WHERE is_superuser=1 ORDER BY id"
                        )
                        != supers
                    ):
                        raise RuntimeError("Cambió un superusuario; se revierte.")
                    if counts["auth_user"] != len(supers):
                        raise RuntimeError("Quedaron otras cuentas; se revierte.")
            finally:
                db.one("SELECT RELEASE_LOCK(%s) AS n", (lock,))
        report = {
            "superusuarios_conservados": len(supers),
            "superusuarios_sin_cambios": True,
            "datos_operativos_vacios": True,
            "conteos": counts,
        }
        destination = config.root / "docs/evidencias/limpieza-base.json"
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=True, indent=2))
    finally:
        database.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "No se completó la limpieza: "
            + type(exc).__name__
            + ". Revisa el respaldo privado.",
            file=sys.stderr,
        )
        raise SystemExit(1)
