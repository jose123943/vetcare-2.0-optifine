"""Previsualiza o aplica la limpieza y carga de demostración con respaldo privado."""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vetcare.config import Config
from vetcare.db import Database
from vetcare.demo import prepare_demo, table_counts
from vetcare.maintenance import snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Borrar datos operativos y cargar ejemplos; conserva superusuarios/configuración.",
    )
    parser.add_argument(
        "--fecha-base",
        type=date.fromisoformat,
        default=datetime.now(ZoneInfo("America/Bogota")).date(),
    )
    parser.add_argument(
        "--test-db", help="Base aislada test_vetcare_ para comprobaciones."
    )
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
                            "conteos_actuales": table_counts(db),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            return
        snapshot(database, backup=True)
        with database.lease() as db:
            locked = db.one(
                "SELECT GET_LOCK(%s,0) AS n", ("vetcare-demo-" + config.database,)
            )
            if locked["n"] != 1:
                raise RuntimeError("Otra carga de demostración está en curso.")
            try:
                with db.atomic():
                    report = prepare_demo(db, args.fecha_base)
            finally:
                db.one(
                    "SELECT RELEASE_LOCK(%s) AS n", ("vetcare-demo-" + config.database,)
                )
        destination = config.root / "docs/demostracion-carga.json"
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        database.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "No se completó la carga: "
            + type(exc).__name__
            + ". El respaldo previo sigue disponible.",
            file=sys.stderr,
        )
        if isinstance(exc, RuntimeError):
            print(str(exc), file=sys.stderr)
        raise SystemExit(1)
